#!/usr/bin/env python3
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    src = REPO_ROOT / "datasets" / "runtime_mindshape" / "cleanroom_seed_records.jsonl"
    rows = load_jsonl(src)
    out_dir = REPO_ROOT / "datasets" / "cleanroom_supervised"
    rep_dir = REPO_ROOT / "reports" / "arc_neuron_small_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    sft = out_dir / "cleanroom_sft.jsonl"
    pref = out_dir / "cleanroom_preference.jsonl"
    trace = out_dir / "cleanroom_trace_receipts.jsonl"

    sft_rows = []
    pref_rows = []
    trace_rows = []
    for i, row in enumerate(rows, 1):
        prompt = row.get("prompt", "")
        target = row.get("target", "")
        constraints = row.get("constraints", [])
        notes = row.get("notes", "")
        sft_rows.append({
            "id": f"cleanroom_sft_{i:03d}",
            "messages": [
                {"role": "system", "content": "You are ARC-Neuron operating inside the cleanroom runtime. Preserve evidence, rollback awareness, and bounded claims."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": target},
            ],
            "constraints": constraints,
            "source_id": row.get("id"),
        })
        pref_rows.append({
            "id": f"cleanroom_pref_{i:03d}",
            "prompt": prompt,
            "chosen": target,
            "rejected": f"Unbounded answer without evidence lane. {notes[:200]}",
            "source_id": row.get("id"),
        })
        trace_rows.append({
            "id": f"cleanroom_trace_{i:03d}",
            "source_id": row.get("id"),
            "lane": row.get("domain", "runtime_doctrine"),
            "capability": row.get("capability", "planning"),
            "receipt": {
                "constraints": constraints,
                "difficulty": row.get("difficulty", "medium"),
                "evidence_summary": notes[:240],
            },
        })

    for path, data in ((sft, sft_rows), (pref, pref_rows), (trace, trace_rows)):
        with path.open("w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    report = {
        "status": "ok",
        "source": str(src.relative_to(REPO_ROOT)),
        "sft_records": len(sft_rows),
        "preference_records": len(pref_rows),
        "trace_records": len(trace_rows),
        "sha256": {
            "sft": sha256(sft.read_bytes()).hexdigest(),
            "preference": sha256(pref.read_bytes()).hexdigest(),
            "trace": sha256(trace.read_bytes()).hexdigest(),
        },
    }
    (rep_dir / "cleanroom_supervised_export_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
