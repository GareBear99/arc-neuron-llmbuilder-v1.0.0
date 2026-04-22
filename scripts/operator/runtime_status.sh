#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="python3"
ORIG_COGNITION_RUNTIME_ADAPTER="${COGNITION_RUNTIME_ADAPTER-}"
ORIG_COGNITION_MODEL_PATH="${COGNITION_MODEL_PATH-}"
ORIG_COGNITION_COMMAND_TEMPLATE="${COGNITION_COMMAND_TEMPLATE-}"
ORIG_COGNITION_EXEMPLAR_ARTIFACT="${COGNITION_EXEMPLAR_ARTIFACT-}"
ORIG_COGNITION_SYSTEM_PROMPT="${COGNITION_SYSTEM_PROMPT-}"
ORIG_COGNITION_TIMEOUT_SECONDS="${COGNITION_TIMEOUT_SECONDS-}"
ORIG_COGNITION_FIRST_OUTPUT_TIMEOUT_SECONDS="${COGNITION_FIRST_OUTPUT_TIMEOUT_SECONDS-}"
ORIG_COGNITION_IDLE_TIMEOUT_SECONDS="${COGNITION_IDLE_TIMEOUT_SECONDS-}"
ORIG_COGNITION_MAX_OUTPUT_BYTES="${COGNITION_MAX_OUTPUT_BYTES-}"
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

echo "Cognition Core local runtime status"
echo "  adapter: ${COGNITION_RUNTIME_ADAPTER:-exemplar}"
echo "  model path: ${COGNITION_MODEL_PATH:-<unset>}"
echo "  command template: ${COGNITION_COMMAND_TEMPLATE:-<unset>}"
echo "  mode: $( [[ "${COGNITION_RUNTIME_ADAPTER:-exemplar}" == "command" ]] && echo 'advanced local GGUF/.llamafile' || echo 'bundled baseline' )"
echo "  exemplar artifact: ${COGNITION_EXEMPLAR_ARTIFACT:-exports/candidates/darpa_functional/exemplar_train/artifact_manifest.json}"
echo "  venv python: $PYTHON_BIN"

if [[ -n "${COGNITION_MODEL_PATH:-}" ]]; then
  if [[ -f "${COGNITION_MODEL_PATH}" ]]; then
    echo "  model file exists: yes"
  else
    echo "  model file exists: no"
  fi
fi

cat <<'MSG'

Next useful checks:
  scripts/operator/run_local_prompt.sh "hello"
  scripts/operator/benchmark_local_model.sh
  "$PYTHON_BIN" scripts/runtime/doctor_direct_runtime.py --help
MSG


if [[ "${COGNITION_RUNTIME_ADAPTER:-exemplar}" == "command" ]]; then
  EXE=""
  if [[ -n "${COGNITION_COMMAND_TEMPLATE:-}" ]]; then
    EXE=$(python3 - <<'PY2'
import os, shlex
cmd=os.environ.get("COGNITION_COMMAND_TEMPLATE","")
parts=shlex.split(cmd) if cmd else []
print(parts[0] if parts else "")
PY2
)
  fi
  if [[ -n "$EXE" ]]; then
    if [[ -x "$EXE" ]] || command -v "$EXE" >/dev/null 2>&1; then
      echo "  command executable exists: yes ($EXE)"
    else
      echo "  command executable exists: no ($EXE)"
    fi
  fi
fi
