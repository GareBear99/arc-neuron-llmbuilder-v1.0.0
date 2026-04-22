#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
python3 scripts/lab/validate_arc_tiny_gguf.py --gguf artifacts/gguf/ARC-Neuron-Small-0.18M-v0.1-F32.gguf
python3 scripts/lab/run_arc_neuron_small_gguf.py --tokens 16
