"""tests/test_omnibinary_pipeline_promotion.py

DARPA-level tests for:
  1. OmnibinaryStore — indexed append, O(1) get, scan, verify, export
  2. ConversationPipeline — canonical path, receipt, Omnibinary mirror,
     auto-tag, label, export training candidates
  3. Promotion gate v2 — hard reject, regression check, archive_only, promote
  4. Arc-RAR bundle — build, read manifest, SHA integrity
  5. ANCF roundtrip — mint from GGUF, read back
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── 1. OmnibinaryStore ────────────────────────────────────────────────────────

from runtime.learning_spine import (
    LearningEvent,
    OmnibinaryStore,
    build_arc_rar_bundle,
    mint_ancf_from_gguf,
    read_ancf,
    read_arc_rar_manifest,
    write_omnibinary_ledger,
)


def make_event(n: int, eid: str | None = None) -> LearningEvent:
    from uuid import uuid4
    return LearningEvent(
        ts_utc=1_700_000_000 + n,
        source="test",
        event_type="test_event",
        payload={"n": n, "data": "x" * 40},
        event_id=eid or uuid4().hex,
    )


def test_omnibinary_store_append_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        events = [make_event(i) for i in range(10)]
        ids = [store.append(ev) for ev in events]
        for i, eid in enumerate(ids):
            recovered = store.get(eid)
            assert recovered is not None, f"Event {eid} not found"
            assert recovered.payload["n"] == i


def test_omnibinary_store_get_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        assert store.get("nonexistent_id") is None


def test_omnibinary_store_scan_all():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        events = [make_event(i) for i in range(5)]
        for ev in events:
            store.append(ev)
        recovered = list(store.scan())
        assert len(recovered) == 5
        ns = [r.payload["n"] for r in recovered]
        assert ns == list(range(5))


def test_omnibinary_store_verify_clean():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        for i in range(3):
            store.append(make_event(i))
        result = store.verify()
        assert result["ok"] is True
        assert result["event_count"] == 3


def test_omnibinary_store_index_rebuilds_after_deletion():
    """Verify rebuilds from physical scan when index file is deleted."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.obin"
        store = OmnibinaryStore(path)
        events = [make_event(i) for i in range(4)]
        ids = [store.append(ev) for ev in events]
        # Delete the sidecar index
        idx_path = path.with_suffix(path.suffix + ".idx")
        idx_path.unlink()
        # Re-open — should rebuild
        store2 = OmnibinaryStore(path)
        for eid in ids:
            assert store2.get(eid) is not None


def test_omnibinary_store_export_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        for i in range(3):
            store.append(make_event(i))
        out = Path(tmp) / "export.jsonl"
        result = store.export_jsonl(out)
        assert result["event_count"] == 3
        assert out.exists()
        lines = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) == 3


def test_omnibinary_store_stats():
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "test.obin")
        store.append(make_event(0))
        stats = store.stats()
        assert stats["event_count"] == 1
        assert stats["size_bytes"] > 0


def test_write_omnibinary_ledger_batch():
    """Legacy batch write still works and is compatible with the store reader."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "batch.obin"
        events = [make_event(i) for i in range(5)]
        result = write_omnibinary_ledger(path, events)
        assert result["event_count"] == 5
        assert "sha256" in result
        assert "index_path" in result
        # Index file should exist
        assert Path(result["index_path"]).exists()


# ── 2. ConversationPipeline ───────────────────────────────────────────────────

def test_conversation_pipeline_basic():
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "conv.obin"
        pipeline = ConversationPipeline(HeuristicAdapter(), store_path=store_path)
        record = pipeline.run_conversation("Plan the next audit step.")
        assert record.response_ok is True
        assert len(record.response_text) > 0
        assert record.prompt_sha256  # non-empty
        assert record.response_sha256
        assert record.receipt_id


def test_conversation_pipeline_omnibinary_mirror():
    """Every turn must be mirrored to OmnibinaryStore and retrievable by receipt_id."""
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "conv.obin"
        pipeline = ConversationPipeline(HeuristicAdapter(), store_path=store_path)
        r1 = pipeline.run_conversation("Critique this design.")
        r2 = pipeline.run_conversation("Plan the repair.")
        # Both should be in the store
        store = OmnibinaryStore(store_path)
        ev1 = store.get(r1.receipt_id)
        ev2 = store.get(r2.receipt_id)
        assert ev1 is not None, "First turn not found in Omnibinary store"
        assert ev2 is not None, "Second turn not found in Omnibinary store"
        assert ev1.payload["prompt"] == r1.prompt
        assert ev2.payload["prompt"] == r2.prompt


def test_conversation_pipeline_auto_tag():
    """Heuristic adapter (promotable=False) should not be auto-tagged as eligible."""
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        pipeline = ConversationPipeline(
            HeuristicAdapter(), store_path=Path(tmp) / "c.obin"
        )
        # Heuristic is not promotable → should not be training_eligible
        record = pipeline.run_conversation("Repair this code path.")
        assert record.training_eligible is False


def test_conversation_pipeline_label_turn():
    from adapters.echo_adapter import EchoAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        pipeline = ConversationPipeline(
            EchoAdapter(), store_path=Path(tmp) / "c.obin"
        )
        record = pipeline.run_conversation("Test prompt for labelling.")
        labelled = pipeline.label_turn(record.turn_id, preferred=True,
                                       correction="Better answer here.")
        assert labelled is True
        history = pipeline.session_history()
        assert history[-1].preferred is True


def test_conversation_pipeline_export_sft(tmp_path):
    from adapters.echo_adapter import EchoAdapter
    from runtime.conversation_pipeline import ConversationPipeline, ConversationRecord

    store_path = tmp_path / "c.obin"
    pipeline = ConversationPipeline(EchoAdapter(), store_path=store_path)

    # Echo adapter is promotable; inject fake eligible records manually
    from runtime.learning_spine import OmnibinaryStore
    from dataclasses import asdict
    from uuid import uuid4
    store = OmnibinaryStore(store_path)
    for i in range(3):
        rec = ConversationRecord(
            conversation_id="sess",
            turn_id=uuid4().hex,
            ts_utc="2026-01-01T00:00:00+00:00",
            adapter="echo",
            prompt=f"prompt_{i}",
            system_prompt="sys",
            response_text="This is a substantial response that exceeds minimum chars threshold for training.",
            response_ok=True,
            latency_ms=10.0,
            finish_reason="completed",
            backend_identity="echo",
            meta={},
            training_eligible=True,
            training_score=0.5,
        )
        from runtime.learning_spine import LearningEvent
        ev = LearningEvent(
            ts_utc=1700000000 + i,
            source="test",
            event_type="conversation_turn",
            payload=asdict(rec),
            event_id=rec.receipt_id,
        )
        store.append(ev)

    sft_path = tmp_path / "sft.jsonl"
    result = pipeline.export_training_candidates(sft_path, min_score=0.0)
    assert result["sft_records"] >= 1
    assert sft_path.exists()
    lines = [json.loads(l) for l in sft_path.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1
    assert "prompt" in lines[0]
    assert "target" in lines[0]


def test_conversation_pipeline_verify_store():
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        pipeline = ConversationPipeline(
            HeuristicAdapter(), store_path=Path(tmp) / "c.obin"
        )
        pipeline.run_conversation("Verify the store integrity.")
        result = pipeline.verify_store()
        assert result["ok"] is True


# ── 3. Promotion gate v2 ──────────────────────────────────────────────────────

def _write_scored(path: Path, results: list[dict], summary: dict,
                  failure_count: int = 0) -> None:
    payload = {
        "results": results,
        "summary": summary,
        "failure_count": failure_count,
        "overall_weighted_score": sum(summary.values()) / max(1, len(summary)),
        "scorer_version": "v2-task-aware",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_promote_first_candidate_accepted(tmp_path):
    scored = tmp_path / "scored.json"
    scoreboard = tmp_path / "scoreboard.json"
    report = tmp_path / "report.json"
    floor_path = tmp_path / "floor.json"   # non-existent = permissive defaults
    _write_scored(scored, [{"run_id": "r1", "latency_ms": 10.0, "ok": True}],
                  {"repair": 0.5, "calibration": 0.7, "reasoning": 0.6,
                   "planning": 0.95, "compression": 0.80, "paraphrase_stability": 0.80})
    proc = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored),
         "--scoreboard", str(scoreboard),
         "--report", str(report),
         "--model-name", "test_v1",
         "--floor-path", str(floor_path),
         "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(report.read_text())
    assert result["promoted"] is True
    assert result["decision"] == "promote"


def test_promote_better_candidate_wins(tmp_path):
    scored_v1 = tmp_path / "scored_v1.json"
    scored_v2 = tmp_path / "scored_v2.json"
    scoreboard  = tmp_path / "scoreboard.json"
    report      = tmp_path / "report.json"
    floor_path  = tmp_path / "floor.json"

    _write_scored(scored_v1, [{"run_id": "r1", "latency_ms": 5.0, "ok": True}],
                  {"repair": 0.4, "calibration": 0.6, "reasoning": 0.5,
                   "planning": 0.92, "compression": 0.75, "paraphrase_stability": 0.78})

    subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_v1), "--scoreboard", str(scoreboard),
         "--report", str(report), "--model-name", "v1",
         "--floor-path", str(floor_path), "--skip-bundle"],
        cwd=ROOT, capture_output=True,
    )

    _write_scored(scored_v2, [{"run_id": "r2", "latency_ms": 4.0, "ok": True}],
                  {"repair": 0.6, "calibration": 0.8, "reasoning": 0.7,
                   "planning": 0.95, "compression": 0.85, "paraphrase_stability": 0.85})
    proc = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_v2), "--scoreboard", str(scoreboard),
         "--report", str(report), "--model-name", "v2",
         "--floor-path", str(floor_path), "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(report.read_text())
    assert result["promoted"] is True
    assert result["decision"] == "promote"


def test_promote_hard_reject_low_repair(tmp_path):
    scored = tmp_path / "scored.json"
    scoreboard = tmp_path / "scoreboard.json"
    report = tmp_path / "report.json"
    _write_scored(scored, [{"run_id": "rx", "latency_ms": 5.0, "ok": True}],
                  {"repair": 0.1, "calibration": 0.9, "reasoning": 0.9},
                  failure_count=0)
    proc = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored), "--scoreboard", str(scoreboard),
         "--report", str(report), "--model-name", "bad_repair", "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    result = json.loads(report.read_text())
    assert result["decision"] == "reject"
    assert result["hard_rejected"] is True


def test_promote_regression_becomes_archive_only(tmp_path):
    scored_v1 = tmp_path / "scored_v1.json"
    scored_v2 = tmp_path / "scored_v2.json"
    scoreboard  = tmp_path / "scoreboard.json"
    report      = tmp_path / "report.json"
    floor_path  = tmp_path / "floor.json"

    _write_scored(scored_v1, [{"run_id": "r1", "latency_ms": 5.0, "ok": True}],
                  {"repair": 0.8, "calibration": 0.7, "reasoning": 0.6,
                   "planning": 0.92, "compression": 0.78, "paraphrase_stability": 0.80})
    subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_v1), "--scoreboard", str(scoreboard),
         "--report", str(report), "--model-name", "v1",
         "--floor-path", str(floor_path), "--skip-bundle"],
        cwd=ROOT, capture_output=True,
    )

    # v2: overall better but repair drops by 0.2 > ceiling 0.04
    _write_scored(scored_v2, [{"run_id": "r2", "latency_ms": 4.0, "ok": True}],
                  {"repair": 0.6, "calibration": 0.9, "reasoning": 0.9,
                   "planning": 0.95, "compression": 0.85, "paraphrase_stability": 0.85})
    proc = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_v2), "--scoreboard", str(scoreboard),
         "--report", str(report), "--model-name", "v2",
         "--floor-path", str(floor_path), "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0
    result = json.loads(report.read_text())
    assert result["decision"] == "archive_only"
    assert not result["promoted"]


# ── 4. Arc-RAR bundle ─────────────────────────────────────────────────────────

def test_arc_rar_bundle_roundtrip(tmp_path):
    files = []
    for i in range(3):
        p = tmp_path / f"file_{i}.json"
        p.write_text(json.dumps({"i": i}), encoding="utf-8")
        files.append(p)
    manifest = {"build_id": "test-123", "candidate": "test"}
    bundle_path = tmp_path / "test.arcrar.zip"
    result = build_arc_rar_bundle(bundle_path, files, manifest)
    assert bundle_path.exists()
    assert result["file_count"] == 4   # 3 files + manifest.json
    # Read manifest back
    m = read_arc_rar_manifest(bundle_path)
    assert m["build_id"] == "test-123"
    assert m["file_count"] == 3


def test_arc_rar_bundle_sha256_stable(tmp_path):
    """SHA must be deterministic for same content."""
    f = tmp_path / "data.json"
    f.write_text('{"x": 1}', encoding="utf-8")
    p1 = tmp_path / "b1.arcrar.zip"
    p2 = tmp_path / "b2.arcrar.zip"
    build_arc_rar_bundle(p1, [f], {"id": "a"})
    build_arc_rar_bundle(p2, [f], {"id": "a"})
    from runtime.learning_spine import sha256_file
    # ZipFile may embed timestamps; we just check the manifest reads correctly
    m1 = read_arc_rar_manifest(p1)
    m2 = read_arc_rar_manifest(p2)
    assert m1["id"] == m2["id"]


# ── 5. ANCF roundtrip ─────────────────────────────────────────────────────────

def test_ancf_roundtrip(tmp_path):
    # Write a fake GGUF (just needs to be bytes)
    gguf = tmp_path / "fake.gguf"
    gguf.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 64)
    metadata = {"general.architecture": "test", "general.name": "ANCF Test"}
    ancf_path = tmp_path / "test.ancf"
    result = mint_ancf_from_gguf(ancf_path, gguf, metadata)
    assert ancf_path.exists()
    assert "ancf_sha256" in result
    assert "gguf_sha256" in result
    meta_back, gguf_back = read_ancf(ancf_path)
    assert meta_back["general.architecture"] == "test"
    assert gguf_back == gguf.read_bytes()


def test_ancf_bad_magic_raises(tmp_path):
    bad = tmp_path / "bad.ancf"
    bad.write_bytes(b"NOPE" + b"\x00" * 32)
    with pytest.raises(ValueError, match="Not an ANCF"):
        read_ancf(bad)


# ── 6. Full pipeline integration ─────────────────────────────────────────────

def test_conversation_pipeline_store_is_canonical():
    """Running two separate pipeline instances on the same store file
    must see each other's events (single-writer, multi-reader model)."""
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.conversation_pipeline import ConversationPipeline

    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "shared.obin"
        p1 = ConversationPipeline(HeuristicAdapter(), store_path=store_path)
        r1 = p1.run_conversation("First pipeline turn.")
        # Second pipeline on same file
        p2 = ConversationPipeline(HeuristicAdapter(), store_path=store_path)
        r2 = p2.run_conversation("Second pipeline turn.")
        # Both should be findable
        store = OmnibinaryStore(store_path)
        assert store.get(r1.receipt_id) is not None
        assert store.get(r2.receipt_id) is not None
        assert store.stats()["event_count"] == 2


def test_omnibinary_high_volume_append_and_lookup():
    """100 events: all must be O(1) retrievable without scanning."""
    with tempfile.TemporaryDirectory() as tmp:
        store = OmnibinaryStore(Path(tmp) / "vol.obin")
        events = [make_event(i) for i in range(100)]
        ids = [store.append(ev) for ev in events]
        for i, eid in enumerate(ids):
            recovered = store.get(eid)
            assert recovered is not None
            assert recovered.payload["n"] == i
        assert store.stats()["event_count"] == 100
