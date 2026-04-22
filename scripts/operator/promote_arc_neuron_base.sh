#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_MODEL_DIR="${1:-}"
if [[ -z "$BASE_MODEL_DIR" ]]; then
  echo "usage: $0 /absolute/path/to/base-model-dir" >&2
  exit 2
fi
if [[ ! -d "$BASE_MODEL_DIR" ]]; then
  echo "base model directory not found: $BASE_MODEL_DIR" >&2
  exit 3
fi
python3 "$ROOT_DIR/scripts/stack/promote_arc_neuron_base_external.py" --base-model "$BASE_MODEL_DIR" --mode external
