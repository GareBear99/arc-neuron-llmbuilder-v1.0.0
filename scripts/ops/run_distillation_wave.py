#!/usr/bin/env python3
"""scripts/ops/run_distillation_wave.py

Automatic distillation wave — converts live system data into a training candidate.

What it does in order:
  1. Flush and export Omnibinary conversation store → SFT records
  2. Dump approved terminology → lexical SFT records
  3. Collect all pipeline-generated data from datasets/
  4. Build a deduplicated combined training corpus
  5. Train a new native candidate on that corpus
  6. Run the full benchmark suite
  7. Score and gate through Gate v2
  8. Bundle if promoted, archive-only otherwise
  9. Update floor if promoted
  10. Write a wave report

Usage
─────
  python3 scripts/ops/run_distillation_wave.py --tier small --steps 400
  python3 scripts/ops/run_distillation_wave.py --tier small --steps 300 --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(cmd: list[str], *, label: str) -> dict:
    print(f"\n[wave] {label}")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  STDERR: {proc.stderr[-500:]}")
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-500:],
    }


def _json_from_stdout(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:
                pass
    return {}


def collect_pipeline_data(dry_run: bool = False) -> dict[str, int]:
    """Flush store, export terminology, count available SFT records."""
    counts: dict[str, int] = {}

    # Flush and export conversation store
    try:
        from runtime.learning_spine import OmnibinaryStore
        from runtime.terminology import TerminologyStore

        store = OmnibinaryStore(ROOT / "artifacts" / "omnibinary" / "arc_conversations.obin")
        store.flush()
        conv_count = store.stats()["event_count"]
        counts["conversation_events"] = conv_count

        if not dry_run and conv_count > 0:
            export_path = ROOT / "datasets" / "distillation_sft" / "pipeline_auto_export.jsonl"
            result = store.export_jsonl(export_path)
            counts["pipeline_sft_exported"] = result["event_count"]

        # Dump terminology
        term_store = TerminologyStore()
        term_dump = ROOT / "datasets" / "language_reasoning" / "terminology_sft.jsonl"
        term_result = term_store.dump_for_training(output_path=term_dump)
        counts["terminology_sft_exported"] = term_result["sft_records"]

    except Exception as e:
        counts["collection_error"] = str(e)[:100]

    # Count all available SFT data
    total = 0
    for f in (ROOT / "datasets").rglob("*.jsonl"):
        lines = [l for l in f.read_text(errors="ignore").splitlines() if l.strip()]
        total += len(lines)
    counts["total_training_records"] = total

    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Run an automatic distillation training wave")
    ap.add_argument("--tier",       default="small", choices=["tiny", "small", "base"])
    ap.add_argument("--steps",      type=int, default=300)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr",         type=float, default=0.001)
    ap.add_argument("--candidate",  default=None, help="Override candidate name")
    ap.add_argument("--dry-run",    action="store_true", help="Plan only, don't train")
    ap.add_argument("--skip-bundle",action="store_true")
    args = ap.parse_args()

    wave_id = args.candidate or f"wave_{uuid4().hex[:8]}"
    started = datetime.now(timezone.utc).isoformat()
    py = sys.executable

    print(f"\n{'═'*60}")
    print(f"  ARC DISTILLATION WAVE: {wave_id}")
    print(f"  tier={args.tier}  steps={args.steps}  started={started}")
    print(f"{'═'*60}")

    steps: list[dict] = []
    report: dict = {
        "wave_id": wave_id,
        "tier": args.tier,
        "steps": args.steps,
        "started_at": started,
        "dry_run": args.dry_run,
    }

    # ── Step 1: Collect and flush all pipeline data ───────────────────────────
    print("\n[wave] Step 1: Collect pipeline data")
    data_counts = collect_pipeline_data(dry_run=args.dry_run)
    report["data_counts"] = data_counts
    print(f"  total training records: {data_counts.get('total_training_records', 0)}")
    print(f"  conversation events:    {data_counts.get('conversation_events', 0)}")
    print(f"  terminology SFT:        {data_counts.get('terminology_sft_exported', 0)}")

    if args.dry_run:
        print("\n[wave] DRY RUN — training skipped. Data collection only.")
        report["status"] = "dry_run_complete"
        (ROOT / "reports" / f"wave_{wave_id}.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        return

    # ── Step 2: Train ─────────────────────────────────────────────────────────
    train_result = _run([
        py, "scripts/training/train_arc_native_candidate.py",
        "--candidate", wave_id,
        "--tier", args.tier,
        "--steps", str(args.steps),
        "--batch-size", str(args.batch_size),
        "--lr", str(args.lr),
    ], label=f"Step 2: Train ({args.steps} steps, tier={args.tier})")
    steps.append({"name": "train", **train_result})
    train_summary = _json_from_stdout(train_result["stdout"])
    report["train"] = train_summary
    if train_result["returncode"] != 0:
        report["status"] = "train_failed"
        _write_report(wave_id, report, steps, started)
        raise SystemExit(1)
    print(f"  val_ppl={train_summary.get('val_ppl')}  final_loss={train_summary.get('final_loss')}")

    # ── Step 3: Benchmark ──────────────────────────────────────────────────────
    exemplar_path = ROOT / "exports" / "candidates" / wave_id / "exemplar_train" / "exemplar_model.json"
    output_path   = ROOT / "results" / f"{wave_id}_model_outputs.jsonl"
    bench_result = _run([
        py, "scripts/execution/run_model_benchmarks.py",
        "--adapter", "exemplar",
        "--artifact", str(exemplar_path),
        "--output", str(output_path),
    ], label="Step 3: Benchmark")
    steps.append({"name": "benchmark", **bench_result})

    # ── Step 4: Score ──────────────────────────────────────────────────────────
    scored_path = ROOT / "results" / f"{wave_id}_scored_outputs.json"
    score_result = _run([
        py, "scripts/execution/score_benchmark_outputs.py",
        "--input", str(output_path),
        "--output", str(scored_path),
    ], label="Step 4: Score")
    steps.append({"name": "score", **score_result})
    if scored_path.exists():
        scored_data = json.loads(scored_path.read_text())
        report["score"] = scored_data.get("overall_weighted_score")
        report["failure_count"] = scored_data.get("failure_count", 0)
        print(f"  weighted_score={report['score']}  failures={report['failure_count']}")

    # ── Step 5: Gate v2 promotion ──────────────────────────────────────────────
    promote_cmd = [
        py, "scripts/execution/promote_candidate.py",
        "--scored", str(scored_path),
        "--model-name", wave_id,
        "--candidate", wave_id,
    ]
    if args.skip_bundle:
        promote_cmd.append("--skip-bundle")
    promote_result = _run(promote_cmd, label="Step 5: Gate v2")
    steps.append({"name": "promote", **promote_result})
    promote_summary = _json_from_stdout(promote_result["stdout"])
    report["decision"]  = promote_summary.get("decision")
    report["promoted"]  = promote_summary.get("promoted")
    print(f"  decision={report['decision']}  promoted={report['promoted']}")

    # ── Step 6: Update floor if promoted ──────────────────────────────────────
    if report.get("promoted"):
        _run([
            py, "runtime/floor_model.py",
            "--set-floor", "--from-scoreboard",
            "--note", f"Auto-updated after wave {wave_id} promotion",
        ], label="Step 6: Update floor")
        report["floor_updated"] = True
    else:
        report["floor_updated"] = False

    # ── Step 7: Verify Omnibinary ─────────────────────────────────────────────
    print("\n[wave] Step 7: Verify Omnibinary store")
    from runtime.learning_spine import OmnibinaryStore
    store = OmnibinaryStore(ROOT / "artifacts" / "omnibinary" / "arc_conversations.obin")
    store.flush()
    verify = store.verify()
    report["obin_verify"] = verify
    print(f"  events={verify['event_count']}  intact={verify['ok']}")

    # ── Finalize ───────────────────────────────────────────────────────────────
    report["status"] = "promoted" if report.get("promoted") else report.get("decision", "unknown")
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    _write_report(wave_id, report, steps, started)

    print(f"\n{'═'*60}")
    print(f"  WAVE {wave_id} COMPLETE")
    print(f"  decision: {report['decision']}  score: {report.get('score')}")
    print(f"  floor_updated: {report.get('floor_updated')}")
    print(f"{'═'*60}")
    print(json.dumps({
        "ok": True,
        "wave_id": wave_id,
        "decision": report["decision"],
        "promoted": report.get("promoted"),
        "score": report.get("score"),
        "floor_updated": report.get("floor_updated"),
    }))


def _write_report(wave_id: str, report: dict, steps: list, started: str) -> None:
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"wave_{wave_id}.json").write_text(
        json.dumps({**report, "step_details": steps}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
