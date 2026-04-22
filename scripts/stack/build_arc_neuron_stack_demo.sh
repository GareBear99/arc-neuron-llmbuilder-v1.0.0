#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$ROOT_DIR/scripts/stack/build_arc_neuron_integrated_demo.py" \
  --zip-input /mnt/data/arc-language-module-main\ \(5\)\(1\).zip \
  --zip-input /mnt/data/ARC-Core-main\ \(18\).zip \
  --zip-input /mnt/data/arc-lucifer-cleanroom-runtime-main\ \(16\).zip \
  --zip-input /mnt/data/omnibinary-runtime-main\ \(1\).zip \
  --zip-input /mnt/data/Arc-RAR-main\ \(3\).zip
python3 "$ROOT_DIR/scripts/lab/validate_arc_tiny_gguf.py" --gguf "$ROOT_DIR/artifacts/gguf/ARC-Neuron-Tiny-Integrated-0.07M-v0.2-F32.gguf"
python3 "$ROOT_DIR/scripts/lab/run_arc_tiny_gguf.py" --gguf "$ROOT_DIR/artifacts/gguf/ARC-Neuron-Tiny-Integrated-0.07M-v0.2-F32.gguf" --tokens 12
