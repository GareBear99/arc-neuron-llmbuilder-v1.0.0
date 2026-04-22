#!/usr/bin/env python3
"""scripts/ops/absorb_session.py

One-command session absorption: take any conversation text or file and push
it through the full language-learning + Omnibinary + training-export pipeline.

This is the practical implementation of "conversation teaches the system immediately."

What it does
────────────
1. Extract terminology (definitions, aliases, corrections) from the text
2. Mirror all new terms to OmnibinaryStore as terminology_event
3. Run the text through the ReflectionLoop for quality improvement
4. Record the improved response as a conversation_turn in OmnibinaryStore
5. Export new training candidates (SFT + preference)
6. Print a receipt summary

Usage
─────
  # Absorb from a text string
  python3 scripts/ops/absorb_session.py --text "Omnibinary means the indexed ledger."

  # Absorb from a file
  python3 scripts/ops/absorb_session.py --file conversation.txt

  # Interactive mode — prompts one at a time
  python3 scripts/ops/absorb_session.py --interactive

  # Absorb and immediately run benchmark to see if it helped
  python3 scripts/ops/absorb_session.py --file session.txt --benchmark
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_incumbent_artifact() -> str | None:
    sb_path = ROOT / "results" / "scoreboard.json"
    if not sb_path.exists():
        return None
    sb = json.loads(sb_path.read_text())
    inc = next((m for m in sb.get("models", []) if m.get("incumbent")), None)
    if inc:
        cand = inc.get("model", "")
        p = ROOT / "exports" / "candidates" / cand / "exemplar_train" / "exemplar_model.json"
        return str(p) if p.exists() else None
    return None


def absorb(text: str, session_id: str, verbose: bool = True) -> dict:
    from runtime.terminology import TerminologyStore
    from runtime.conversation_pipeline import ConversationPipeline
    from runtime.reflection_loop import ReflectionLoop

    results: dict = {
        "session_id":       session_id,
        "ts":               datetime.now(timezone.utc).isoformat(),
        "new_terms":        0,
        "obin_events":      0,
        "training_records": 0,
    }

    # 1. Terminology absorption
    term_store = TerminologyStore()
    new_terms = term_store.absorb_from_conversation(text, session_id=session_id)
    results["new_terms"] = len(new_terms)
    if verbose and new_terms:
        print(f"  [terminology] +{len(new_terms)} terms learned:")
        for t in new_terms[:5]:
            print(f"    '{t.term}' ({t.record_type}): {t.value[:60]}...")

    # 2. Export terminology to training data
    term_sft = term_store.dump_for_training()
    if verbose:
        print(f"  [terminology] {term_sft['sft_records']} total SFT records in terminology store")

    # 3. Run text through pipeline as a structured conversation turn
    artifact = get_incumbent_artifact()
    if artifact:
        from adapters.exemplar_adapter import ExemplarAdapter
        base = ExemplarAdapter(artifact=artifact, top_k=3)
    else:
        from adapters.heuristic_adapter import HeuristicAdapter
        base = HeuristicAdapter()

    adapter = ReflectionLoop(base, skip_on_short=60)
    store_path = ROOT / "artifacts" / "omnibinary" / "arc_conversations.obin"
    pipeline = ConversationPipeline(adapter, store_path=store_path, conversation_id=session_id)

    # Split text into prompts (paragraphs > 30 chars)
    prompts = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if not prompts:
        prompts = [text[:500]] if text.strip() else []

    eligible_count = 0
    for prompt in prompts[:6]:   # cap at 6 turns per absorption
        rec = pipeline.run_conversation(prompt)
        if rec.training_eligible:
            eligible_count += 1

    stats = pipeline.store_stats()
    results["obin_events"] = stats["event_count"]

    # 4. Export training candidates
    sft_out = ROOT / "datasets" / "distillation_sft" / f"absorbed_{session_id[:8]}.jsonl"
    export = pipeline.export_training_candidates(sft_out, min_score=0.15)
    results["training_records"] = export.get("sft_records", 0)
    results["sft_path"] = str(sft_out.relative_to(ROOT))

    if verbose:
        print(f"  [pipeline]    {eligible_count}/{len(prompts)} turns eligible for training")
        print(f"  [pipeline]    {results['training_records']} SFT records exported")
        print(f"  [omnibinary]  {stats['event_count']} total events in store")

    return results


def run_benchmark_after(session_id: str) -> dict:
    import subprocess
    artifact = get_incumbent_artifact()
    if not artifact:
        return {"skipped": True, "reason": "no incumbent artifact"}
    out_path = ROOT / "results" / f"post_absorb_{session_id[:8]}_outputs.jsonl"
    scored_path = ROOT / "results" / f"post_absorb_{session_id[:8]}_scored.json"
    subprocess.run(
        [sys.executable, "scripts/execution/run_model_benchmarks.py",
         "--adapter", "exemplar", "--artifact", artifact,
         "--output", str(out_path)],
        cwd=ROOT, capture_output=True,
    )
    subprocess.run(
        [sys.executable, "scripts/execution/score_benchmark_outputs.py",
         "--input", str(out_path), "--output", str(scored_path)],
        cwd=ROOT, capture_output=True,
    )
    if scored_path.exists():
        sc = json.loads(scored_path.read_text())
        return {"score": sc.get("overall_weighted_score"), "scored_path": str(scored_path.relative_to(ROOT))}
    return {"skipped": True, "reason": "scoring failed"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Absorb a conversation into the ARC language+memory system")
    ap.add_argument("--text",        default=None, help="Text to absorb directly")
    ap.add_argument("--file",        default=None, help="Path to text file to absorb")
    ap.add_argument("--session-id",  default=None, help="Session ID (auto-generated if not set)")
    ap.add_argument("--benchmark",   action="store_true", help="Run benchmark after absorption")
    ap.add_argument("--interactive", action="store_true", help="Interactive prompt mode")
    ap.add_argument("--quiet",       action="store_true")
    args = ap.parse_args()

    from uuid import uuid4
    session_id = args.session_id or f"absorb_{uuid4().hex[:8]}"
    verbose = not args.quiet

    if args.interactive:
        print("[absorb] Interactive mode — type prompts (empty line to finish):")
        lines = []
        while True:
            try:
                line = input("> ")
                if not line.strip():
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        text = "\n\n".join(lines)
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8", errors="ignore")
    elif args.text:
        text = args.text
    else:
        ap.print_help()
        return

    if not text.strip():
        print("[absorb] No text to absorb.")
        return

    print(f"[absorb] Session: {session_id}")
    print(f"[absorb] Text: {len(text)} chars")
    results = absorb(text, session_id=session_id, verbose=verbose)

    if args.benchmark:
        print("[absorb] Running post-absorption benchmark...")
        bench = run_benchmark_after(session_id)
        results["benchmark"] = bench
        print(f"[absorb] Post-absorption score: {bench.get('score', 'N/A')}")

    print(json.dumps({"ok": True, **results}, indent=2))


if __name__ == "__main__":
    main()
