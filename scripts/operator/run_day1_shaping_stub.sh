#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python scripts/training/prepare_distillation_corpus.py
python scripts/training/train_lora_candidate.py
python scripts/training/train_preference_candidate.py
python scripts/training/merge_adapters_stub.py
echo "Day 1 shaping stub complete. Replace stubs with real trainer execution."
