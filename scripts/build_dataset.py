from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def count_jsonl_records(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                json.loads(line)
                count += 1
    return count


def main() -> None:
    base = ROOT / "data"
    totals = {}
    for file in sorted(base.rglob("*.jsonl")):
        totals[str(file.relative_to(ROOT))] = count_jsonl_records(file)
    print(json.dumps({"dataset_counts": totals, "dataset_total_records": sum(totals.values())}, indent=2))


if __name__ == "__main__":
    main()
