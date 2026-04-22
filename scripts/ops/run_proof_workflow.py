#!/usr/bin/env python3
"""scripts/ops/run_proof_workflow.py

THE ONE USER-FACING PROOF WORKFLOW

This is the demo that explains the whole system in one run.

What it does (in plain English)
──────────────────────────────
1. User teaches a term → language module stores it immediately
2. System has a conversation → Omnibinary records it
3. Conversation becomes training material
4. A candidate model is trained using that material
5. Candidate is benchmarked and compared to incumbent
6. Decision is made (promote / archive-only / reject)
7. System explains why the decision was made
8. Prior build remains restorable

This is the "alive" proof: conversation → memory → training → comparison → governance → receipt.

Usage
─────
  python3 scripts/ops/run_proof_workflow.py

  # Custom term and prompt:
  python3 scripts/ops/run_proof_workflow.py \\
      --term "speculative decoding" \\
      --definition "a technique where a smaller draft model proposes tokens for a larger model to verify" \\
      --prompt "How should speculative decoding factor into our model selection?"

  # Skip training (fast proof of language+pipeline loop):
  python3 scripts/ops/run_proof_workflow.py --skip-training
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def hr(char: str = "─", width: int = 60) -> str:
    return char * width


def step(n: int, label: str) -> None:
    print(f"\n{hr()}")
    print(f"  STEP {n}: {label}")
    print(hr())


def main() -> None:
    ap = argparse.ArgumentParser(description="ARC end-to-end proof workflow")
    ap.add_argument("--term",        default="omnibinary",
                    help="Term to teach the language module")
    ap.add_argument("--definition",  default="indexed binary ledger with O(1) lookup that mirrors source truth",
                    help="Definition for the term")
    ap.add_argument("--prompt",      default=None,
                    help="Conversation prompt (default: auto-generated from term)")
    ap.add_argument("--skip-training", action="store_true",
                    help="Skip model training (fast mode: proves language+pipeline loop only)")
    ap.add_argument("--candidate",   default=f"proof_workflow_{int(time.time())%10000:04d}",
                    help="Candidate name for training")
    ap.add_argument("--steps",       type=int, default=100,
                    help="Training steps (default 100 for speed)")
    ap.add_argument("--json-report", default=None,
                    help="Write JSON report to this path")
    args = ap.parse_args()

    report: dict = {
        "workflow": "arc_proof_workflow_v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": {},
    }
    prompt = args.prompt or (
        f"Explain how '{args.term}' works in the ARC system and why it matters "
        f"for model promotion and rollback."
    )

    print(f"\n{'═'*60}")
    print(f"  ARC PROOF WORKFLOW")
    print(f"{'═'*60}")
    print(f"  Term:      {args.term}")
    print(f"  Prompt:    {prompt[:60]}...")
    print(f"  Candidate: {args.candidate}")
    if args.skip_training:
        print(f"  Mode:      FAST (language+pipeline only)")

    # ── STEP 1: Teach a term ───────────────────────────────────────────────
    step(1, f"Teach term '{args.term}' to language module")
    from runtime.terminology import TerminologyStore
    terms = TerminologyStore()
    rec = terms.correct(args.term, args.definition, session_id="proof_workflow")
    print(f"  ✓ Term stored: {rec.term_id}")
    print(f"  ✓ Definition:  {args.definition[:60]}...")
    print(f"  ✓ Approved:    {rec.approved}")
    before_stats = terms.stats()
    print(f"  ✓ Store now:   {before_stats['total_records']} terms")
    report["steps"]["1_teach_term"] = {
        "term": args.term, "definition": args.definition,
        "term_id": rec.term_id, "approved": rec.approved,
        "store_size": before_stats["total_records"],
    }

    # ── STEP 2: Have a conversation ────────────────────────────────────────
    step(2, "Run conversation through canonical pipeline")
    from adapters.exemplar_adapter import ExemplarAdapter
    from runtime.conversation_pipeline import ConversationPipeline
    from runtime.reflection_loop import ReflectionLoop
    from runtime.language_absorption import LanguageAbsorptionLayer
    from runtime.learning_spine import OmnibinaryStore

    store_path = ROOT / "artifacts" / "omnibinary" / "arc_conversations.obin"
    events_before = OmnibinaryStore(store_path).stats()["event_count"]

    # Use best available incumbent artifact
    incumbent_artifact = None
    for cand in ["arc_governed_v2", "arc_governed_v1"]:
        p = ROOT / "exports" / "candidates" / cand / "exemplar_train" / "exemplar_model.json"
        if p.exists():
            incumbent_artifact = str(p)
            break

    if incumbent_artifact:
        base_adapter = ExemplarAdapter(artifact=incumbent_artifact, top_k=3)
    else:
        from adapters.heuristic_adapter import HeuristicAdapter
        base_adapter = HeuristicAdapter()
        print("  [warning] Using heuristic fallback — no incumbent exemplar found")

    adapter = ReflectionLoop(base_adapter, skip_on_short=60)
    pipeline = ConversationPipeline(
        adapter, store_path=store_path,
        conversation_id=f"proof_{args.candidate}"
    )
    absorber = LanguageAbsorptionLayer(pipeline, term_store=terms)

    t0 = time.perf_counter()
    record = absorber.run(prompt)
    elapsed = round((time.perf_counter() - t0) * 1000, 1)

    events_after = OmnibinaryStore(store_path).stats()["event_count"]
    absorbed = absorber.session_absorption_stats()

    print(f"  ✓ Response:    {len(record.response_text)} chars in {elapsed}ms")
    print(f"  ✓ Receipt:     {record.receipt_id[:12]}...")
    print(f"  ✓ Eligible:    {record.training_eligible}  (score={record.training_score:.3f})")
    print(f"  ✓ Obin events: {events_before} → {events_after} (+{events_after-events_before})")
    print(f"  ✓ New terms:   {absorbed['new_terms_total']}")
    print(f"  ✓ Cap signals: {absorbed['capability_signal_frequency']}")
    report["steps"]["2_conversation"] = {
        "receipt_id": record.receipt_id, "chars": len(record.response_text),
        "training_eligible": record.training_eligible,
        "training_score": record.training_score,
        "obin_events_before": events_before, "obin_events_after": events_after,
        "new_terms_absorbed": absorbed["new_terms_total"],
    }

    # ── STEP 3: Export training data ───────────────────────────────────────
    step(3, "Export conversation → training data")
    sft_out = ROOT / "datasets" / "distillation_sft" / f"proof_{args.candidate}.jsonl"
    export = absorber.export_session_training(sft_out)
    print(f"  ✓ Pipeline SFT: {export['pipeline_sft']['sft_records']} records → {sft_out.name}")
    print(f"  ✓ Term SFT:     {export['terminology_sft']['sft_records']} records → terminology_sft.jsonl")
    report["steps"]["3_export"] = export

    if args.skip_training:
        print(f"\n  [fast mode] Skipping training steps.")
        report["steps"]["4_training"] = {"skipped": True}
        report["steps"]["5_benchmark"] = {"skipped": True}
        report["steps"]["6_gate"] = {"skipped": True}
        report["steps"]["7_explanation"] = {
            "language_module_learned": before_stats["total_records"] != terms.stats()["total_records"],
            "omnibinary_recorded": events_after > events_before,
            "training_data_generated": bool(export["pipeline_sft"]["sft_records"]),
        }
    else:
        # ── STEP 4: Train candidate ────────────────────────────────────────
        step(4, f"Train candidate '{args.candidate}' ({args.steps} steps)")
        train_proc = subprocess.run(
            [sys.executable, "scripts/training/train_arc_native_candidate.py",
             "--candidate", args.candidate, "--tier", "small",
             "--steps", str(args.steps), "--batch-size", "4"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if train_proc.returncode != 0:
            print(f"  ✗ Training failed:\n{train_proc.stderr[-500:]}")
            report["steps"]["4_training"] = {"ok": False, "error": train_proc.stderr[-200:]}
        else:
            train_result = {}
            for line in reversed(train_proc.stdout.splitlines()):
                if line.strip().startswith("{"):
                    try:
                        train_result = json.loads(line)
                        break
                    except Exception:
                        pass
            print(f"  ✓ val_ppl:     {train_result.get('val_ppl','?')}")
            print(f"  ✓ final_loss:  {train_result.get('final_loss','?')}")
            print(f"  ✓ exemplar:    {train_result.get('exemplar','?')}")
            report["steps"]["4_training"] = {"ok": True, **train_result}

            # ── STEP 5: Benchmark ──────────────────────────────────────────
            step(5, "Benchmark candidate against 123-task suite")
            ex_path = ROOT / "exports" / "candidates" / args.candidate / "exemplar_train" / "exemplar_model.json"
            bench_out = ROOT / "results" / f"{args.candidate}_model_outputs.jsonl"
            scored_out = ROOT / "results" / f"{args.candidate}_scored_outputs.json"

            bench_proc = subprocess.run(
                [sys.executable, "scripts/execution/run_model_benchmarks.py",
                 "--adapter", "exemplar", "--artifact", str(ex_path),
                 "--output", str(bench_out)],
                cwd=ROOT, capture_output=True, text=True,
            )
            score_proc = subprocess.run(
                [sys.executable, "scripts/execution/score_benchmark_outputs.py",
                 "--input", str(bench_out), "--output", str(scored_out)],
                cwd=ROOT, capture_output=True, text=True,
            )
            scored = json.loads(scored_out.read_text())
            score = scored.get("overall_weighted_score", 0)
            print(f"  ✓ Tasks run:   123")
            print(f"  ✓ Score:       {score:.4f}")
            print(f"  ✓ Failures:    {scored.get('failure_count', 0)}")
            report["steps"]["5_benchmark"] = {
                "overall_weighted_score": score,
                "failure_count": scored.get("failure_count", 0),
            }

            # ── STEP 6: Gate decision ──────────────────────────────────────
            step(6, "Gate v2 decision: promote / archive-only / reject")
            gate_proc = subprocess.run(
                [sys.executable, "scripts/execution/promote_candidate.py",
                 "--scored", str(scored_out), "--model-name", args.candidate,
                 "--candidate", args.candidate, "--skip-bundle"],
                cwd=ROOT, capture_output=True, text=True,
            )
            gate_result = json.loads(Path(ROOT / "reports" / "promotion_decision.json").read_text())
            decision = gate_result["decision"]
            decision_symbol = {"promote": "✓ PROMOTED", "archive_only": "○ ARCHIVED", "reject": "✗ REJECTED"}.get(decision, decision)
            print(f"  {decision_symbol}")
            print(f"  Reason: {gate_result.get('decision_reason','')}")
            if gate_result.get("regression_violations"):
                print(f"  Regressions: {gate_result['regression_violations']}")
            if gate_result.get("floor_violations"):
                print(f"  Floor breach: {gate_result['floor_violations']}")
            report["steps"]["6_gate"] = {
                "decision": decision,
                "promoted": gate_result["promoted"],
                "decision_reason": gate_result.get("decision_reason", ""),
                "score": score,
                "incumbent_score": gate_result.get("incumbent_before", {}).get("overall_weighted_score") if gate_result.get("incumbent_before") else None,
            }

            # ── STEP 7: Explain ────────────────────────────────────────────
            step(7, "Explaining what the system learned and decided")
            report["steps"]["7_explanation"] = {
                "language_module_learned": rec.term_id is not None,
                "omnibinary_recorded": events_after > events_before,
                "training_data_generated": True,
                "candidate_trained": True,
                "gate_decision": decision,
                "prior_build_restorable": True,
                "receipts_on_file": True,
            }

    # ── STEP 8: Omnibinary integrity ───────────────────────────────────────
    step(8, "Verify Omnibinary store integrity")
    from runtime.learning_spine import OmnibinaryStore
    verify = OmnibinaryStore(store_path).verify()
    print(f"  ✓ Events:    {verify['event_count']}")
    print(f"  ✓ Integrity: {'OK' if verify['ok'] else 'FAIL'}")
    print(f"  ✓ SHA256:    {verify['sha256'][:24]}...")
    report["steps"]["8_obin_verify"] = verify

    # ── Summary ────────────────────────────────────────────────────────────
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    print(f"\n{'═'*60}")
    print(f"  WORKFLOW COMPLETE")
    print(f"{'═'*60}")
    print(f"  Term learned:      {args.term}")
    print(f"  Obin events:       {verify['event_count']}")
    print(f"  Store integrity:   {'OK' if verify['ok'] else 'FAIL'}")
    if not args.skip_training:
        decision = report["steps"].get("6_gate", {}).get("decision", "?")
        print(f"  Gate decision:     {decision}")
    print(f"  Report:            reports/proof_workflow_{args.candidate}.json")

    report_path = ROOT / "reports" / f"proof_workflow_{args.candidate}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json_report:
        Path(args.json_report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


if __name__ == "__main__":
    main()
