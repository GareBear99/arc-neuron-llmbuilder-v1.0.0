#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python scripts/training/export_gguf_candidate.py
python scripts/execution/run_quantization_retention.py
python scripts/execution/promote_candidate.py
echo "Day 2 export/promotion stub complete. Replace export path with real candidate artifacts."
