#!/usr/bin/env python3
"""scripts/ops/generate_reflection_sft.py

Generate draft→critique→revise training pairs using the ReflectionLoop.

These pairs teach the model to:
  1. Notice overconfident claims
  2. Detect missing constraints
  3. Produce better-calibrated final answers

Output: datasets/distillation_sft/reflection_sft.jsonl
        datasets/distillation_preference/reflection_preference.jsonl

Usage
─────
  python3 scripts/ops/generate_reflection_sft.py
  python3 scripts/ops/generate_reflection_sft.py --candidate arc_governed_v2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Seed prompts designed to produce improvable draft answers
SEED_PROMPTS = [
    # Overconfidence traps — draft should overclaim, revision should be bounded
    ("calibration", "Will the next trained candidate definitely score higher than arc_governed_v2?"),
    ("calibration", "Is the ARC system guaranteed to produce better models every generation?"),
    ("calibration", "Can I be certain that the floor model will prevent all regressions?"),
    # Missing constraint traps — draft should miss constraints, revision should add them
    ("planning", "Plan how to deploy a new model to production."),
    ("planning", "Describe the steps to promote a candidate model."),
    ("planning", "Explain how to improve model quality quickly."),
    # Contradiction traps — draft may be inconsistent, revision should resolve
    ("reasoning", "Should we ever skip the benchmark step if training loss is very low?"),
    ("reasoning", "Is it acceptable to use a heuristic adapter as the comparison baseline?"),
    ("reasoning", "Can we promote a candidate without running the full gate?"),
    # Revision quality — draft should be rough, revision should be cleaner
    ("repair", "Fix this broken process: we train models, save them somewhere, and hope the next one is better."),
    ("repair", "Improve this workflow: run benchmarks, look at results, decide manually."),
    ("compression", "Summarize everything about the ARC system in as much detail as possible."),
    # Self-correction practice
    ("reflection", "Critique this statement: 'The system is now a conscious AI because it has memory.'"),
    ("reflection", "Critique this claim: 'A higher score always means a better model in every way.'"),
    ("reflection", "Review this decision: 'We archived v3 even though it scored 0.6128 vs v2 at 0.6247.'"),
]


def generate_reflection_pairs(artifact: str | None, n_pairs: int = len(SEED_PROMPTS)) -> list[dict]:
    from adapters.exemplar_adapter import ExemplarAdapter
    from adapters.heuristic_adapter import HeuristicAdapter
    from runtime.reflection_loop import ReflectionLoop, _extract_field

    # Use best available adapter
    if artifact and Path(artifact).exists():
        try:
            base = ExemplarAdapter(artifact=artifact, top_k=3)
            print(f"[reflection-sft] Using exemplar adapter: {artifact}")
        except Exception:
            base = HeuristicAdapter()
            print("[reflection-sft] Fallback: heuristic adapter")
    else:
        base = HeuristicAdapter()
        print("[reflection-sft] Using heuristic adapter")

    loop = ReflectionLoop(base, skip_on_short=40)
    pairs: list[dict] = []

    for i, (capability, prompt) in enumerate(SEED_PROMPTS[:n_pairs]):
        response = loop.generate(prompt, system_prompt="Plan, critique, repair, calibrate.")
        reflection = response.meta.get("reflection", {})
        draft    = reflection.get("draft", "")
        critique = reflection.get("critique", "")
        revised  = reflection.get("revised", "")
        skipped  = reflection.get("skipped", False)

        if skipped or not draft:
            print(f"  [{i+1:2d}/{n_pairs}] skipped (too short)")
            continue

        final = revised if revised else draft
        fix_str = _extract_field(critique, "FIX") if critique else ""
        fix_needed = bool(fix_str and "none" not in fix_str.lower())

        # SFT pair: prompt → final (best) answer
        sft = {
            "prompt":         prompt,
            "target":         final,
            "capability":     capability,
            "source":         "reflection_loop_sft",
            "draft":          draft,
            "critique":       critique,
            "revised":        revised,
            "fix_needed":     fix_needed,
        }
        pairs.append(sft)
        status = "REVISED" if revised else "draft"
        print(f"  [{i+1:2d}/{n_pairs}] {status:7s}  cap={capability:12s}  chars={len(final):4d}")

    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default=None)
    ap.add_argument("--n", type=int, default=len(SEED_PROMPTS))
    args = ap.parse_args()

    artifact = None
    if args.candidate:
        artifact = str(ROOT / "exports" / "candidates" / args.candidate / "exemplar_train" / "exemplar_model.json")
    else:
        # Auto-discover incumbent
        sb_path = ROOT / "results" / "scoreboard.json"
        if sb_path.exists():
            sb = json.loads(sb_path.read_text())
            inc = next((m for m in sb.get("models", []) if m.get("incumbent")), None)
            if inc:
                cand = inc.get("model", "")
                artifact = str(ROOT / "exports" / "candidates" / cand / "exemplar_train" / "exemplar_model.json")
                print(f"[reflection-sft] Auto-selected incumbent: {cand}")

    print(f"[reflection-sft] Generating {args.n} reflection pairs...")
    pairs = generate_reflection_pairs(artifact, n_pairs=args.n)

    # SFT output
    sft_out = ROOT / "datasets" / "distillation_sft" / "reflection_sft.jsonl"
    sft_out.parent.mkdir(parents=True, exist_ok=True)
    with sft_out.open("w", encoding="utf-8") as f:
        for p in pairs:
            sft_rec = {
                "prompt":     p["prompt"],
                "target":     p["target"],
                "capability": p["capability"],
                "source":     p["source"],
            }
            f.write(json.dumps(sft_rec, ensure_ascii=False) + "\n")

    # Preference output (draft=rejected, revised=chosen where fix_needed)
    pref_out = ROOT / "datasets" / "distillation_preference" / "reflection_preference.jsonl"
    pref_count = 0
    with pref_out.open("w", encoding="utf-8") as f:
        for p in pairs:
            if p["fix_needed"] and p["draft"] and p["revised"]:
                pref = {
                    "prompt":   p["prompt"],
                    "chosen":   p["revised"],
                    "rejected": p["draft"],
                    "source":   "reflection_loop_preference",
                }
                f.write(json.dumps(pref, ensure_ascii=False) + "\n")
                pref_count += 1

    print(f"\n[reflection-sft] SFT records:        {len(pairs)} → {sft_out.relative_to(ROOT)}")
    print(f"[reflection-sft] Preference pairs:   {pref_count} → {pref_out.relative_to(ROOT)}")
    print(json.dumps({"ok": True, "sft": len(pairs), "preference": pref_count}, indent=2))


if __name__ == "__main__":
    main()
