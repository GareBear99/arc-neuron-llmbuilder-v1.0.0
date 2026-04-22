from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    scoreboard = Path("results/scoreboard.json")
    if not scoreboard.exists():
        print(json.dumps({"warning": "results/scoreboard.json not found"}, indent=2))
        return
    data = json.loads(scoreboard.read_text(encoding="utf-8"))
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
