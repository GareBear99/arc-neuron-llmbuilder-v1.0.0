#!/usr/bin/env python3
"""scripts/ops/bundle_promoted_candidate.py

Package a promoted candidate into an Arc-RAR archive (.arcrar.zip) containing:
  - artifact_manifest.json   (lora_train + merge + gguf_export manifests)
  - promotion_decision.json  (the promotion report)
  - scored_outputs.json      (benchmark evidence)
  - model checkpoint (.pt) if under size limit
  - GGUF artifact if under size limit
  - receipts (runtime_receipt_*.json)
  - this bundle's own manifest.json

The result is a single signed-by-hash archive that can be:
  - stored indefinitely
  - restored to roll back to this exact state
  - shared as a traceable model release artifact

Usage
─────
  python3 scripts/ops/bundle_promoted_candidate.py --candidate my_candidate

  # Also bundle GGUF (may be large):
  python3 scripts/ops/bundle_promoted_candidate.py \\
      --candidate my_candidate --include-gguf

  # Specify a GGUF path directly:
  python3 scripts/ops/bundle_promoted_candidate.py \\
      --candidate my_candidate \\
      --gguf artifacts/gguf/ARC-Neuron-Small-0.18M-v0.1-F32.gguf
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.learning_spine import build_arc_rar_bundle, sha256_file


MAX_BUNDLE_FILE_MB = 500   # skip files larger than this unless forced


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _collect_receipts(root: Path, candidate: str) -> list[Path]:
    receipts = list((root / "reports").glob(f"runtime_receipt_{candidate}*.json"))
    receipts += list((root / "reports" / "user_runs").glob("*.json"))
    return [p for p in receipts if p.exists()][:10]   # cap at 10 most recent


def main() -> None:
    ap = argparse.ArgumentParser(description="Bundle a promoted candidate into Arc-RAR")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--gguf", default=None, help="Path to GGUF artifact (optional)")
    ap.add_argument("--include-gguf", action="store_true",
                    help="Auto-discover and include GGUF checkpoint")
    ap.add_argument("--force-large", action="store_true",
                    help=f"Include files over {MAX_BUNDLE_FILE_MB}MB size limit")
    ap.add_argument("--out-dir", default=None,
                    help="Output directory (default: artifacts/archives/)")
    args = ap.parse_args()

    cand = args.candidate
    cand_dir = ROOT / "exports" / "candidates" / cand
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "artifacts" / "archives"
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle_id = f"arc-rar-{cand}-{uuid4().hex[:8]}"
    out_path = out_dir / f"{bundle_id}.arcrar.zip"

    # ── collect files to bundle ────────────────────────────────────────────
    files_to_bundle: list[Path] = []
    skipped: list[str] = []

    def maybe_add(p: Path) -> None:
        if not p.exists():
            return
        size_mb = p.stat().st_size / (1 << 20)
        if size_mb > MAX_BUNDLE_FILE_MB and not args.force_large:
            skipped.append(f"{p.name} ({size_mb:.1f}MB — skipped, use --force-large)")
            return
        files_to_bundle.append(p)

    # Stage manifests — archived with stage-qualified names to avoid collision
    stage_files_map: dict[str, Path] = {}
    for stage in ("lora_train", "merge", "gguf_export", "exemplar_train", "preference_train"):
        p = cand_dir / stage / "artifact_manifest.json"
        if p.exists():
            stage_files_map[f"{stage}_manifest.json"] = p

    # Benchmark evidence
    maybe_add(ROOT / "reports" / "promotion_decision.json")
    maybe_add(ROOT / "results" / "scored_outputs.json")
    maybe_add(ROOT / "reports" / "quantization_retention_report.json")

    # Receipts
    for p in _collect_receipts(ROOT, cand):
        maybe_add(p)

    # Checkpoint (.pt)
    for pt in (cand_dir / "lora_train" / "checkpoint").glob("*.pt"):
        maybe_add(pt)

    # GGUF
    gguf_path: Path | None = None
    if args.gguf:
        gguf_path = Path(args.gguf)
    elif args.include_gguf:
        # Auto-discover in gguf_export or checkpoint
        for search in [
            cand_dir / "gguf_export",
            cand_dir / "lora_train" / "checkpoint",
            ROOT / "artifacts" / "gguf",
        ]:
            hits = list(search.glob("*.gguf")) if search.exists() else []
            if hits:
                gguf_path = sorted(hits)[-1]
                break
    if gguf_path and gguf_path.exists():
        maybe_add(gguf_path)

    # ── load constituent manifests for the bundle manifest ─────────────────
    lora_manifest = _load_json(cand_dir / "lora_train" / "artifact_manifest.json")
    promo_report  = _load_json(ROOT / "reports" / "promotion_decision.json")
    score_summary = _load_json(ROOT / "results" / "scored_outputs.json")

    bundle_manifest = {
        "bundle_id": bundle_id,
        "bundle_format": "arc-rar-v1",
        "candidate": cand,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_status": lora_manifest.get("status", "unknown"),
        "execution_mode": lora_manifest.get("execution_mode", "unknown"),
        "tier": lora_manifest.get("tier", "unknown"),
        "promoted": promo_report.get("promoted", False),
        "decision_reason": promo_report.get("decision_reason", ""),
        "overall_weighted_score": score_summary.get("overall_weighted_score", 0.0),
        "param_count": lora_manifest.get("param_count"),
        "training": lora_manifest.get("training", {}),
        "lineage": {
            "parent_candidate": (promo_report.get("incumbent_before") or {}).get("model") if promo_report else None,
            "parent_score": (promo_report.get("incumbent_before") or {}).get("overall_weighted_score") if promo_report else None,
        },
        "stage_manifests": list(stage_files_map.keys()),
        "files_included": list(stage_files_map.keys()) + [p.name for p in files_to_bundle],
        "files_skipped": skipped,
        "sha256_index": {
            **{name: sha256_file(path) for name, path in stage_files_map.items()},
            **{p.name: sha256_file(p) for p in files_to_bundle},
        },
    }

    # ── build the bundle ───────────────────────────────────────────────────
    # build_arc_rar_bundle takes list[Path]; for named stage manifests we
    # write them into the ZIP directly with custom arcname via a custom call.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import zipfile as _zf
    from datetime import datetime as _dt, timezone as _tz
    bundle_ts = _dt.now(_tz.utc).isoformat()
    bm_with_ts = {**bundle_manifest, "bundled_at": bundle_ts, "file_count": len(bundle_manifest["files_included"])}
    with _zf.ZipFile(out_path, "w", compression=_zf.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(bm_with_ts, indent=2, sort_keys=True))
        # Stage manifests with qualified names
        for arcname, src_path in stage_files_map.items():
            if src_path.exists():
                zf.write(src_path, arcname=arcname)
        # Regular files
        for file_path in files_to_bundle:
            if file_path.exists():
                zf.write(file_path, arcname=file_path.name)
    result = {"path": str(out_path), "sha256": sha256_file(out_path),
              "file_count": len(bundle_manifest["files_included"]) + 1}

    # Write report
    report_path = ROOT / "reports" / f"arc_rar_bundle_{cand}.json"
    report = {
        "ok": True,
        "bundle_id": bundle_id,
        "candidate": cand,
        "bundle_path": str(out_path.relative_to(ROOT)),
        "sha256": result["sha256"],
        "file_count": result["file_count"],
        "files_included": bundle_manifest["files_included"],
        "files_skipped": skipped,
        "promoted": bundle_manifest["promoted"],
        "overall_weighted_score": bundle_manifest["overall_weighted_score"],
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if skipped:
        print(f"\n  [info] {len(skipped)} file(s) skipped due to size limit:")
        for s in skipped:
            print(f"    - {s}")


if __name__ == "__main__":
    main()
