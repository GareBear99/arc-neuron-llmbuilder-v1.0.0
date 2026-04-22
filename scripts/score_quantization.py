from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path("results/scoreboard.json")
    if not path.exists():
        print(json.dumps({"warning": "No scoreboard found"}, indent=2))
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({"quantization_report_source": data}, indent=2))


if __name__ == "__main__":
    main()
