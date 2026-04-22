#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python -m pip install -e .[dev] >/dev/null
python scripts/version_audit.py
pytest -q
bash scripts/smoke.sh
python -m lucifer_runtime.cli export --jsonl release_events.jsonl --sqlite-backup release_backup.sqlite3 >/dev/null

echo "release check ok"
