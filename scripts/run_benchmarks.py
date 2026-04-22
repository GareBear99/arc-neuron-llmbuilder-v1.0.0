from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def load_tasks(folder: Path) -> int:
    total = 0
    for file in sorted(folder.rglob("*.jsonl")):
        with file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    json.loads(line)
                    total += 1
    return total


def main() -> None:
    bench_root = ROOT / "benchmarks"
    summary = {}
    for child in sorted(bench_root.iterdir()):
        if child.is_dir():
            summary[child.name] = load_tasks(child)
    print(json.dumps({"benchmark_task_counts": summary, "benchmark_total_tasks": sum(summary.values())}, indent=2))


if __name__ == "__main__":
    main()
