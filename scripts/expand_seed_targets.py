from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> None:
    target_dataset = 20
    target_benchmark = 10
    report = {"datasets": {}, "benchmarks": {}}
    for path in sorted((ROOT / "data").rglob("*.jsonl")):
        n = count_jsonl(path)
        report["datasets"][str(path.relative_to(ROOT))] = {"count": n, "target": target_dataset, "ready": n >= target_dataset}
    for path in sorted((ROOT / "benchmarks").rglob("*.jsonl")):
        n = count_jsonl(path)
        report["benchmarks"][str(path.relative_to(ROOT))] = {"count": n, "target": target_benchmark, "ready": n >= target_benchmark}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
