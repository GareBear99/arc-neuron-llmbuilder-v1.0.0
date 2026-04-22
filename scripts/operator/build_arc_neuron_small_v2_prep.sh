#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/stack/build_arc_neuron_small_v2_prep.py
