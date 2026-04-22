#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ORIG_COGNITION_RUNTIME_ADAPTER="${COGNITION_RUNTIME_ADAPTER-}"
ORIG_COGNITION_MODEL_PATH="${COGNITION_MODEL_PATH-}"
ORIG_COGNITION_COMMAND_TEMPLATE="${COGNITION_COMMAND_TEMPLATE-}"
ORIG_COGNITION_EXEMPLAR_ARTIFACT="${COGNITION_EXEMPLAR_ARTIFACT-}"
ORIG_COGNITION_SYSTEM_PROMPT="${COGNITION_SYSTEM_PROMPT-}"
ORIG_COGNITION_TIMEOUT_SECONDS="${COGNITION_TIMEOUT_SECONDS-}"
ORIG_COGNITION_FIRST_OUTPUT_TIMEOUT_SECONDS="${COGNITION_FIRST_OUTPUT_TIMEOUT_SECONDS-}"
ORIG_COGNITION_IDLE_TIMEOUT_SECONDS="${COGNITION_IDLE_TIMEOUT_SECONDS-}"
ORIG_COGNITION_MAX_OUTPUT_BYTES="${COGNITION_MAX_OUTPUT_BYTES-}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

if [[ -f .env.direct-runtime ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.direct-runtime
  set +a
elif [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

ADAPTER="${COGNITION_RUNTIME_ADAPTER:-exemplar}"
PROMPT="${1:-Say hello, identify your runtime mode, and state one next action.}"

echo "[1/4] Runtime status"
scripts/operator/runtime_status.sh

echo
if [[ "$ADAPTER" == "command" ]]; then
  echo "[2/4] Direct runtime doctor"
  "$PYTHON_BIN" scripts/runtime/doctor_direct_runtime.py --adapter command
else
  echo "[2/4] Direct runtime doctor"
  "$PYTHON_BIN" scripts/runtime/doctor_direct_runtime.py --adapter exemplar --artifact "${COGNITION_EXEMPLAR_ARTIFACT:-$ROOT/exports/candidates/darpa_functional/exemplar_train/artifact_manifest.json}"
fi

echo

echo "[3/4] Prompt smoke"
scripts/operator/run_local_prompt.sh "$PROMPT"

echo

echo "[4/4] Benchmark smoke"
scripts/operator/benchmark_local_model.sh

echo
cat <<MSG
Flagship runtime validation completed.
This confirms the local runtime path can:
- resolve the configured adapter
- run the runtime doctor
- answer a direct prompt
- complete a benchmark pass
MSG
