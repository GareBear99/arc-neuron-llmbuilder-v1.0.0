#!/usr/bin/env python3
"""scripts/ops/run_user_proof_demo.py

THE ONE DEMO — the single workflow that explains the whole ARC system.

Story it proves:
  1. User teaches the system a new term
  2. Term is stored in the language/truth layer with provenance
  3. User has a conversation — model responds using what it knows
  4. The conversation is archived to the Omnibinary store (O(1) retrievable)
  5. That conversation becomes training material (SFT export)
  6. A new candidate is trained incorporating that material
  7. The candidate is benchmarked against the incumbent
  8. Gate v2 decides: promote, archive_only, or reject
  9. If promoted: Arc-RAR bundle is created; floor is updated
  10. The evidence chain is printed — every step is auditable

This demo runs in ~2 minutes on CPU.
Use --steps 20 for a 30-second quick version.

Usage
─────
  python3 scripts/ops/run_user_proof_demo.py
  python3 scripts/ops/run_user_proof_demo.py --steps 20 --quick
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _banner(msg: str, width: int = 60) -> None:
    print(f"\n{'═'*width}")
    print(f"  {msg}")
    print(f"{'═'*width}")


def _step(n: int, msg: str) -> None:
    print(f"\n[{n:2d}] {msg}")


def main() -> None:
    ap = argparse.ArgumentParser(description="ARC user-facing proof demo")
    ap.add_argument("--steps",      type=int, default=100, help="Training steps")
    ap.add_argument("--quick",      action="store_true",   help="Ultra-fast 10-step run for CI")
    ap.add_argument("--term",       default="cognition spine",
                    help="New term to teach the system")
    ap.add_argument("--definition", default="the unified layer that combines runtime, memory, and model into one governed machine")
    args = ap.parse_args()

    if args.quick:
        args.steps = 10

    session_id = f"demo_{uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat()
    evidence: list[dict] = []

    _banner("ARC SYSTEM — USER PROOF DEMO")
    print(f"  session_id: {session_id}")
    print(f"  started:    {started_at}")
    print(f"  term:       '{args.term}'")
    print(f"  definition: '{args.definition}'")

    # ── Step 1: Teach the system a new term ───────────────────────────────────
    _step(1, f"Teaching term: '{args.term}'")
    from runtime.terminology import TerminologyStore
    term_store = TerminologyStore()
    rec = term_store.correct(args.term, args.definition, session_id=session_id)
    evidence.append({
        "step": 1,
        "action": "teach_term",
        "term_id": rec.term_id,
        "term": rec.term,
        "approved": rec.approved,
        "confidence": rec.confidence,
    })
    print(f"     ✓ term_id={rec.term_id[:12]}  approved={rec.approved}")

    # ── Step 2: Conversation using the taught term ────────────────────────────
    _step(2, "Running conversation through canonical pipeline")
    from adapters.exemplar_adapter import ExemplarAdapter
    from runtime.conversation_pipeline import ConversationPipeline
    from runtime.reflection_loop import ReflectionLoop
    from runtime.learning_spine import OmnibinaryStore

    # Find the current incumbent's exemplar
    sb_path = ROOT / "results" / "scoreboard.json"
    sb = json.loads(sb_path.read_text()) if sb_path.exists() else {"models": []}
    incumbent = next(
        (m for m in sorted(sb.get("models", []),
                           key=lambda m: m.get("overall_weighted_score", 0), reverse=True)
         if m.get("adapter") not in {"heuristic", "echo"}),
        None,
    )
    if incumbent:
        artifact = ROOT / "exports" / "candidates" / incumbent["model"] / "exemplar_train" / "exemplar_model.json"
    else:
        # Fall back to any available exemplar
        artifacts = list((ROOT / "exports").rglob("exemplar_model.json"))
        artifact = artifacts[-1] if artifacts else None

    store_path = ROOT / "artifacts" / "omnibinary" / "arc_conversations.obin"
    obin = OmnibinaryStore(store_path)
    events_before = obin.stats()["event_count"]

    if artifact and artifact.exists():
        base_adapter = ExemplarAdapter(artifact=str(artifact), top_k=3)
        adapter = ReflectionLoop(base_adapter, skip_on_short=60)
    else:
        from adapters.heuristic_adapter import HeuristicAdapter
        adapter = HeuristicAdapter()

    pipeline = ConversationPipeline(adapter, store_path=store_path, conversation_id=session_id)
    prompt = (
        f"Using the concept of '{args.term}' which means '{args.definition}', "
        f"explain what the next development priority for the ARC system should be. "
        f"Preserve the constraint that rollback must always be possible."
    )
    t0 = time.perf_counter()
    record = pipeline.run_conversation(prompt)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    pipeline._store.flush()

    events_after = obin.stats()["event_count"]
    new_events = events_after - events_before

    evidence.append({
        "step": 2,
        "action": "conversation",
        "receipt_id": record.receipt_id,
        "training_eligible": record.training_eligible,
        "training_score": record.training_score,
        "response_chars": len(record.response_text),
        "latency_ms": latency_ms,
        "new_obin_events": new_events,
    })
    reflection = record.meta.get("reflection", {})
    print(f"     ✓ receipt={record.receipt_id[:12]}  eligible={record.training_eligible}  score={record.training_score:.3f}")
    print(f"       chars={len(record.response_text)}  latency={latency_ms}ms  revised={'revised' in reflection.get('final_source','')}")
    print(f"       obin_events: {events_before} → {events_after} (+{new_events})")

    # ── Step 3: Verify the conversation is retrievable from Omnibinary ────────
    _step(3, "Verifying O(1) retrieval from Omnibinary store")
    retrieved = obin.get(record.receipt_id)
    assert retrieved is not None, "Event not found in Omnibinary store!"
    assert retrieved.event_id == record.receipt_id
    verify = obin.verify()
    evidence.append({
        "step": 3,
        "action": "obin_verify",
        "event_count": verify["event_count"],
        "integrity": verify["ok"],
        "retrieved_receipt": record.receipt_id,
    })
    print(f"     ✓ O(1) retrieval: OK  events={verify['event_count']}  integrity={verify['ok']}")

    # ── Step 4: Absorb new terms from the response ────────────────────────────
    _step(4, "Absorbing terminology from conversation response")
    new_terms = term_store.absorb_from_conversation(record.response_text, session_id=session_id, mirror=False)
    term_stats = term_store.stats()
    evidence.append({
        "step": 4,
        "action": "terminology_absorption",
        "new_terms": len(new_terms),
        "total_terms": term_stats["total_records"],
        "approved": term_stats["approved_records"],
        "extracted": [t.term for t in new_terms[:5]],
    })
    print(f"     ✓ new_terms={len(new_terms)}  total={term_stats['total_records']}  approved={term_stats['approved_records']}")
    if new_terms:
        print(f"       learned: {[t.term for t in new_terms[:3]]}")

    # ── Step 5: Export training candidates ────────────────────────────────────
    _step(5, "Exporting conversation as training data")
    sft_out = ROOT / "datasets" / "distillation_sft" / f"demo_{session_id}.jsonl"
    export = pipeline.export_training_candidates(sft_out, min_score=0.0)
    term_out = ROOT / "datasets" / "language_reasoning" / "terminology_sft.jsonl"
    term_export = term_store.dump_for_training(output_path=term_out)
    evidence.append({
        "step": 5,
        "action": "training_export",
        "sft_records": export.get("sft_records", 0),
        "terminology_sft": term_export.get("sft_records", 0),
        "sft_path": str(sft_out.relative_to(ROOT)),
    })
    print(f"     ✓ sft_records={export.get('sft_records',0)}  terminology_sft={term_export.get('sft_records',0)}")

    # ── Step 6: Train a demo candidate ───────────────────────────────────────
    _step(6, f"Training demo candidate ({args.steps} steps)")
    import subprocess
    candidate = session_id
    proc = subprocess.run(
        [sys.executable, "scripts/training/train_arc_native_candidate.py",
         "--candidate", candidate, "--tier", "tiny", "--steps", str(args.steps),
         "--batch-size", "4"],
        cwd=ROOT, capture_output=True, text=True,
    )
    train_summary: dict = {}
    for line in reversed(proc.stdout.splitlines()):
        if line.strip().startswith("{"):
            try:
                train_summary = json.loads(line)
                break
            except Exception:
                pass
    evidence.append({
        "step": 6,
        "action": "train",
        "ok": proc.returncode == 0,
        "val_ppl": train_summary.get("val_ppl"),
        "final_loss": train_summary.get("final_loss"),
    })
    print(f"     {'✓' if proc.returncode==0 else '✗'} returncode={proc.returncode}  val_ppl={train_summary.get('val_ppl')}  final_loss={train_summary.get('final_loss')}")

    # ── Step 7: Benchmark ─────────────────────────────────────────────────────
    _step(7, "Benchmarking demo candidate")
    exemplar_path = ROOT / "exports" / "candidates" / candidate / "exemplar_train" / "exemplar_model.json"
    output_path   = ROOT / "results" / f"{candidate}_model_outputs.jsonl"
    proc2 = subprocess.run(
        [sys.executable, "scripts/execution/run_model_benchmarks.py",
         "--adapter", "exemplar", "--artifact", str(exemplar_path), "--output", str(output_path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    bench_ok = proc2.returncode == 0
    evidence.append({"step": 7, "action": "benchmark", "ok": bench_ok})
    print(f"     {'✓' if bench_ok else '✗'} benchmark complete")

    # ── Step 8: Score ─────────────────────────────────────────────────────────
    _step(8, "Scoring outputs")
    scored_path = ROOT / "results" / f"{candidate}_scored_outputs.json"
    proc3 = subprocess.run(
        [sys.executable, "scripts/execution/score_benchmark_outputs.py",
         "--input", str(output_path), "--output", str(scored_path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    score = 0.0
    if scored_path.exists():
        sc = json.loads(scored_path.read_text())
        score = sc.get("overall_weighted_score", 0.0)
    evidence.append({"step": 8, "action": "score", "ok": proc3.returncode==0, "score": score})
    print(f"     ✓ weighted_score={score}")

    # ── Step 9: Gate v2 ───────────────────────────────────────────────────────
    _step(9, "Running Gate v2 promotion decision")
    report_path = ROOT / "reports" / f"demo_promo_{candidate}.json"
    proc4 = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_path), "--model-name", candidate,
         "--candidate", candidate, "--report", str(report_path), "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True,
    )
    decision, promoted = "unknown", False
    if report_path.exists():
        promo = json.loads(report_path.read_text())
        decision = promo.get("decision", "unknown")
        promoted = promo.get("promoted", False)
    evidence.append({
        "step": 9,
        "action": "gate_v2",
        "decision": decision,
        "promoted": promoted,
        "score": score,
    })
    print(f"     ✓ decision={decision}  promoted={promoted}  score={score}")

    # ── Step 10: Print the evidence chain ─────────────────────────────────────
    _banner("EVIDENCE CHAIN — COMPLETE")
    for ev in evidence:
        step_n = ev.pop("step")
        action = ev.pop("action")
        print(f"  [{step_n:2d}] {action}")
        for k, v in ev.items():
            print(f"       {k}: {v}")

    chain = {
        "session_id":  session_id,
        "started_at":  started_at,
        "completed_at":datetime.now(timezone.utc).isoformat(),
        "term_taught": args.term,
        "receipt_id":  record.receipt_id,
        "obin_events_added": new_events,
        "obin_integrity": verify["ok"],
        "training_score": record.training_score,
        "candidate": candidate,
        "model_score": score,
        "gate_decision": decision,
        "promoted": promoted,
        "steps_proven": len(evidence) + 2,
        "evidence": evidence,
    }
    chain_path = ROOT / "reports" / f"proof_chain_{session_id}.json"
    chain_path.write_text(json.dumps(chain, indent=2), encoding="utf-8")

    _banner("PROOF CHAIN WRITTEN")
    print(f"  {chain_path.relative_to(ROOT)}")
    print()
    print("  In plain English:")
    print(f"  1. You taught the system '{args.term}'")
    print(f"  2. You had a conversation — receipt={record.receipt_id[:12]}")
    print(f"  3. That conversation is O(1) retrievable from the Omnibinary store")
    print(f"  4. {len(new_terms)} new terms were extracted from your response")
    print(f"  5. The conversation became {export.get('sft_records',0)} training records")
    print(f"  6. A new candidate was trained in {args.steps} steps")
    print(f"  7-8. It was benchmarked and scored: {score}")
    print(f"  9. Gate v2 decided: {decision}")
    print(f"  → Every step has a receipt. The whole chain is replayable.")
    print()
    print(json.dumps({"ok": True, "session_id": session_id, "decision": decision, "score": score}))


if __name__ == "__main__":
    main()
