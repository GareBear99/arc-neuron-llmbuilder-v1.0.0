from __future__ import annotations

import json
from pathlib import Path


def build_attachment_record(image_path: str) -> dict:
    return {
        "kind": "screenshot_attachment",
        "image_path": image_path,
        "source": "ai-screenshot-attachment",
        "status": "captured_or_registered",
    }


def main() -> None:
    path = "examples/attachments/sample_attachment_record.json"
    rec = build_attachment_record("/tmp/browser_screenshot_example.png")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": path}, indent=2))


if __name__ == "__main__":
    main()
