#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python scripts/execution/check_local_backend.py
python scripts/execution/bootstrap_experiment.py
python scripts/execution/run_full_candidate_gate.py
python scripts/execution/generate_readiness_report.py
echo "Day 0 candidate run complete. Inspect results/ and reports/."
