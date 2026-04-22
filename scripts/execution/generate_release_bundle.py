from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
OUT = DIST / "cognition-core-release-bundle.zip"

SKIP_DIRS = {"__pycache__", ".pytest_cache", "dist"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix in SKIP_SUFFIXES:
        return False
    return path.is_file()


def main() -> None:
    count = 0
    with ZipFile(OUT, "w", compression=ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if should_include(path):
                zf.write(path, path.relative_to(ROOT))
                count += 1
    print(json.dumps({"ok": True, "bundle": str(OUT.relative_to(ROOT)), "files": count}, indent=2))


if __name__ == "__main__":
    main()
