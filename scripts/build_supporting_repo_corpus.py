from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_PRESETS = {
    "cleanroom": {"dataset": "runtime_mindshape", "capability": "planning", "domain": "runtime_doctrine", "difficulty": "medium"},
    "arc_core": {"dataset": "system_of_record", "capability": "reasoning", "domain": "state_and_evidence", "difficulty": "hard"},
    "omnibinary": {"dataset": "execution_lane_reasoning", "capability": "reasoning", "domain": "execution_lane", "difficulty": "hard"},
    "arc_rar": {"dataset": "receipt_archive", "capability": "repair", "domain": "archive_and_receipts", "difficulty": "medium"},
    "language_module": {"dataset": "language_reasoning", "capability": "calibration", "domain": "language_systems", "difficulty": "medium"},
    "claude_pressure": {"dataset": "workflow_pressure", "capability": "critique", "domain": "workflow_pressure", "difficulty": "hard"},
}

MD_EXTS = {".md", ".markdown", ".txt"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_doc(name: str) -> int:
    lowered = name.lower()
    score = 0
    for token in [
        "architecture",
        "doctrine",
        "readme",
        "audit",
        "plan",
        "runtime",
        "evidence",
        "workflow",
        "repair",
        "integration",
        "contract",
        "state",
        "translation",
        "cache",
        "decoder",
    ]:
        if token in lowered:
            score += 2
    if lowered.endswith(".md"):
        score += 1
    return score


def extract_summary(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        if ln.startswith("#"):
            out.append(ln.lstrip("# ").strip())
        elif re.match(r"^[A-Za-z0-9][A-Za-z0-9 ,:/()_\-]{20,}$", ln):
            out.append(ln)
        if len(" | ".join(out)) > 320:
            break
    summary = " | ".join(out)[:500].strip(" |")
    return summary or "No concise summary extracted."


def infer_prompt(preset: dict, summary: str, name: str) -> str:
    domain = preset["domain"].replace("_", " ")
    return (
        f"Using the source document '{name}', explain the strongest {domain} lessons that should shape cognition-core "
        f"while preserving bounded, evidence-aware behavior.\n\nSource summary: {summary}"
    )


def infer_target(preset: dict, summary: str, name: str) -> str:
    capability = preset["capability"]
    if capability == "planning":
        return f"Preserve narrow changes, explicit sequencing, rollback awareness, and evidence-linked validation. Derived from {name}: {summary}"
    if capability == "reasoning":
        return f"Separate facts from inferences, classify the operating lane correctly, and surface blockers honestly. Derived from {name}: {summary}"
    if capability == "repair":
        return f"Archive before mutate, keep repairs surgical, and emit receipts with replay lineage. Derived from {name}: {summary}"
    if capability == "calibration":
        return f"State what is known, unknown, and provider-dependent without overclaiming coverage. Derived from {name}: {summary}"
    return f"Critique the workflow, preserve constraints, and avoid synthetic overclaiming. Derived from {name}: {summary}"


def iter_docs_from_source(source: Path, limit: int) -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            candidates = [n for n in zf.namelist() if not n.startswith("__MACOSX/") and Path(n).suffix.lower() in MD_EXTS]
            candidates.sort(key=score_doc, reverse=True)
            for name in candidates[: limit * 4]:
                try:
                    text = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                docs.append((name, text))
                if len(docs) >= limit:
                    break
    else:
        candidates = [p for p in source.rglob("*") if p.suffix.lower() in MD_EXTS]
        candidates.sort(key=lambda p: score_doc(str(p)), reverse=True)
        for path in candidates[:limit]:
            docs.append((str(path.relative_to(source)), path.read_text(encoding="utf-8", errors="ignore")))
    return docs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Path to source zip or extracted repo root")
    ap.add_argument("--package", required=True, choices=sorted(PACKAGE_PRESETS))
    ap.add_argument("--limit", type=int, default=12)
    args = ap.parse_args()

    preset = PACKAGE_PRESETS[args.package]
    out_dir = ROOT / "datasets" / preset["dataset"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.package}_seed_records.jsonl"
    manifest_path = ROOT / "reports" / f"{args.package}_source_ingestion_manifest.json"

    source = Path(args.source)
    docs = iter_docs_from_source(source, args.limit)

    records = []
    top_documents = []
    for idx, (name, text) in enumerate(docs, start=1):
        summary = extract_summary(text)
        records.append(
            {
                "id": f"{args.package}_{idx:03d}",
                "source_repo": args.package,
                "source_file": name,
                "capability": preset["capability"],
                "domain": preset["domain"],
                "difficulty": preset["difficulty"],
                "prompt": infer_prompt(preset, summary, name),
                "target": infer_target(preset, summary, name),
                "constraints": [
                    "Stay grounded in source summary",
                    "Do not overclaim unsupported runtime capability",
                ],
                "notes": summary,
            }
        )
        top_documents.append({"path": name, "summary": summary[:200]})

    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    manifest = {
        "source_name": args.package,
        "source_path": str(source),
        "output_path": str(out_path.relative_to(ROOT)),
        "records_written": len(records),
        "doc_count": len(docs),
        "created_at": now(),
        "top_documents": top_documents[:10],
        "notes": "Curated markdown/doc extraction for cognition-core corpus shaping. Review before training.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
