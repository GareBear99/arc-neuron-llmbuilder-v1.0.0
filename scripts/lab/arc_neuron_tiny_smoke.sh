#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GGUF_PATH="${1:-$ROOT_DIR/artifacts/gguf/ARC-Neuron-Tiny-0.05M-v0.1-F32.gguf}"
python3 "$ROOT_DIR/scripts/lab/validate_arc_tiny_gguf.py" --gguf "$GGUF_PATH"
python3 "$ROOT_DIR/scripts/lab/run_arc_tiny_gguf.py" --gguf "$GGUF_PATH" --tokens 16
