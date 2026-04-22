from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=False)
    parser.add_argument("--output", default="examples/attachments/sample_attachment_record.json")
    args = parser.parse_args()
    record = {
        "kind": "screenshot_attachment",
        "image_path": args.image or "<external_capture>",
        "status": "registered",
        "note": "Use integrations/ai-screenshot-attachment for upstream capture plumbing."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out)}, indent=2))

if __name__ == "__main__":
    main()
