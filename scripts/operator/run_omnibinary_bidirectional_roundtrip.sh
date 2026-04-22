#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LANG_DB="$ROOT/ecosystem/arc-language-module/data/arc_language.db"
OBIN_OUT="$ROOT/artifacts/omnibinary_bridge/arc_language_truth_v1.obin"
MANIFEST_OUT="$ROOT/artifacts/omnibinary_bridge/arc_language_truth_v1.manifest.json"
RESTORE_DB="$ROOT/artifacts/omnibinary_bridge/arc_language_truth_v1.restored.db"
REPORT_OUT="$ROOT/reports/omnibinary_bridge/arc_language_truth_v1_roundtrip.json"
python3 "$ROOT/scripts/stack/omnibinary_language_bridge.py" export --db "$LANG_DB" --out "$OBIN_OUT" --manifest "$MANIFEST_OUT"
python3 "$ROOT/scripts/stack/omnibinary_language_bridge.py" import --binary "$OBIN_OUT" --out-db "$RESTORE_DB" --report "$REPORT_OUT"
echo "Omnibinary <-> language-module roundtrip complete."
