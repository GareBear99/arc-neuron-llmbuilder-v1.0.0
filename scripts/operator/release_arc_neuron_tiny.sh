#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/operator/write_arc_neuron_release_manifest.py"
python3 "$ROOT/scripts/lab/validate_arc_tiny_gguf.py"
printf '\nARC-Neuron Tiny release manifest written and tiny GGUF validated.\n'
