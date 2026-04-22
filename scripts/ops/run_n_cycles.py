#!/usr/bin/env python3
"""scripts/ops/run_n_cycles.py

Run N governed promotion cycles and record the evidence.

DARPA requires repeatable proof, not one lucky cycle. This script runs
the full train→benchmark→gate loop N times, records every result, and
produces a repeatability report showing whether the loop is stable.

Usage
─────
  python3 scripts/ops/run_n_cycles.py --cycles 3 --tier tiny --steps 30
  python3 scripts/ops/run_n_cycles.py --cycles 5 --tier small --steps 200
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_cycle(n: int, tier: str, steps: int, batch: int) -> dict:
    ts = datetime.now(timezone.utc).strftime("%H%M%SZ")
    candidate = f"cycle_{n:02d}_{ts}"
    result: dict = {"cycle": n, "candidate": candidate, "ok": False}

    print(f"\n  ── Cycle {n} ─────────────────────────────────────")

    # Train
    train = subprocess.run(
        [sys.executable, "scripts/training/train_arc_native_candidate.py",
         "--candidate", candidate, "--tier", tier, "--steps", str(steps),
         "--batch-size", str(batch)],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    if train.returncode != 0:
        result["error"] = "training_failed"
        print(f"    ✗ Training failed")
        return result

    # Parse training result
    for line in reversed(train.stdout.splitlines()):
        if line.strip().startswith("{"):
            try:
                tr = json.loads(line)
                result["val_ppl"] = tr.get("val_ppl")
                result["final_loss"] = tr.get("final_loss")
                break
            except Exception:
                pass
    print(f"    ✓ Trained: val_ppl={result.get('val_ppl','?'):.3f}  loss={result.get('final_loss','?'):.4f}")

    # Benchmark
    artifact = ROOT / "exports" / "candidates" / candidate / "exemplar_train" / "exemplar_model.json"
    bench_out = ROOT / "results" / f"{candidate}_outputs.jsonl"
    bench = subprocess.run(
        [sys.executable, "scripts/execution/run_model_benchmarks.py",
         "--adapter", "exemplar", "--artifact", str(artifact),
         "--output", str(bench_out)],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )
    if bench.returncode != 0:
        result["error"] = "benchmark_failed"
        print(f"    ✗ Benchmark failed")
        return result

    # Score
    scored_out = ROOT / "results" / f"{candidate}_scored.json"
    score = subprocess.run(
        [sys.executable, "scripts/execution/score_benchmark_outputs.py",
         "--input", str(bench_out), "--output", str(scored_out)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    if score.returncode == 0 and scored_out.exists():
        sc = json.loads(scored_out.read_text())
        result["score"] = sc.get("overall_weighted_score", 0.0)
        result["failure_count"] = sc.get("failure_count", 0)
    print(f"    ✓ Scored:  {result.get('score','?'):.4f}  failures={result.get('failure_count',0)}")

    # Promote
    report_path = ROOT / "reports" / f"cycle_{n:02d}_{ts}_promo.json"
    gate = subprocess.run(
        [sys.executable, "scripts/execution/promote_candidate.py",
         "--scored", str(scored_out), "--model-name", candidate,
         "--candidate", candidate, "--report", str(report_path),
         "--skip-bundle"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    if gate.returncode == 0 and report_path.exists():
        rpt = json.loads(report_path.read_text())
        result["decision"]  = rpt.get("decision", "unknown")
        result["promoted"]  = rpt.get("promoted", False)
        result["floor_violations"] = rpt.get("floor_violations", [])
        result["regression_violations"] = rpt.get("regression_violations", [])
    print(f"    ✓ Gate:    {result.get('decision','?').upper()}  promoted={result.get('promoted')}")

    result["ok"] = True
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Run N governed promotion cycles")
    ap.add_argument("--cycles",  type=int, default=3)
    ap.add_argument("--tier",    default="tiny", choices=["tiny", "small", "base"])
    ap.add_argument("--steps",   type=int, default=30)
    ap.add_argument("--batch",   type=int, default=4)
    args = ap.parse_args()

    print(f"\n{'═'*60}")
    print(f"  ARC REPEATABILITY RUN: {args.cycles} cycles  tier={args.tier}  steps={args.steps}")
    print(f"{'═'*60}")

    cycles: list[dict] = []
    for n in range(1, args.cycles + 1):
        result = run_cycle(n, tier=args.tier, steps=args.steps, batch=args.batch)
        cycles.append(result)

    # Analysis
    ok_cycles     = [c for c in cycles if c.get("ok")]
    promoted      = [c for c in ok_cycles if c.get("promoted")]
    archive_only  = [c for c in ok_cycles if c.get("decision") == "archive_only"]
    rejected      = [c for c in ok_cycles if c.get("decision") == "reject"]
    scores        = [c["score"] for c in ok_cycles if "score" in c]
    floor_hits    = [c for c in ok_cycles if c.get("floor_violations")]
    reg_hits      = [c for c in ok_cycles if c.get("regression_violations")]

    summary = {
        "total_cycles":    args.cycles,
        "completed":       len(ok_cycles),
        "promoted":        len(promoted),
        "archive_only":    len(archive_only),
        "rejected":        len(rejected),
        "floor_breaches":  len(floor_hits),
        "regressions":     len(reg_hits),
        "score_min":       round(min(scores), 4) if scores else None,
        "score_max":       round(max(scores), 4) if scores else None,
        "score_mean":      round(sum(scores)/len(scores), 4) if scores else None,
        "loop_stable":     len(ok_cycles) == args.cycles and len(rejected) == 0,
    }

    report = {
        "run_at":  datetime.now(timezone.utc).isoformat(),
        "config":  {"cycles": args.cycles, "tier": args.tier, "steps": args.steps},
        "cycles":  cycles,
        "summary": summary,
    }
    report_path = ROOT / "reports" / f"repeatability_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'═'*60}")
    print("  REPEATABILITY SUMMARY")
    print(f"{'═'*60}")
    for k, v in summary.items():
        print(f"  {k:25s}: {v}")
    verdict = "✓ STABLE" if summary["loop_stable"] else "✗ UNSTABLE"
    print(f"\n  Verdict: {verdict}")
    print(f"  Report:  {report_path.relative_to(ROOT)}")
    print(f"{'═'*60}")

    print(json.dumps({"ok": True, **summary, "report": str(report_path.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
