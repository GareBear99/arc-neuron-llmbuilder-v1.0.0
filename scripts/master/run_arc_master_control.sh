#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"
PHASE="${1:-status}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT_DIR/reports/master_operator/$TIMESTAMP"
mkdir -p "$REPORT_DIR"

log() { printf '[ARC-MASTER] %s\n' "$*"; }
run_step() {
  local name="$1"; shift
  log "RUN $name"
  { "$@"; } >"$REPORT_DIR/${name}.log" 2>&1
  log "OK  $name"
}

status_summary() {
  cat <<TXT
ARC Unified Stack Master Control
root: $ROOT_DIR
phase: $PHASE
reports: $REPORT_DIR

Available phases:
  status
  truth-latch
  tiny-floor
  small-build
  small-v2-prep
  base-prep
  full-native-cycle
TXT
}

write_summary_json() {
python3 - <<PY
import json, os, pathlib, sys
root = pathlib.Path(${ROOT_DIR@Q})
report_dir = pathlib.Path(${REPORT_DIR@Q})
phase = ${PHASE@Q}
summary = {
    "phase": phase,
    "root": str(root),
    "report_dir": str(report_dir),
    "artifacts": {
        "tiny_gguf": str(root / "artifacts/gguf/ARC-Neuron-Tiny-0.05M-v0.1-F32.gguf"),
        "small_gguf": str(root / "artifacts/gguf/ARC-Neuron-Small-0.18M-v0.1-F32.gguf"),
        "small_tokenizer_prep": str(root / "artifacts/tokenizer/arc_neuron_small_v0.2_tokenizer.json"),
        "truth_obin": str(root / "artifacts/omnibinary_bridge/arc_language_truth_v1.obin"),
    },
}
(report_dir / "master_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
}

case "$PHASE" in
  status)
    status_summary | tee "$REPORT_DIR/status.txt"
    write_summary_json
    ;;
  truth-latch)
    run_step omnibinary_language_roundtrip bash scripts/operator/run_omnibinary_bidirectional_roundtrip.sh
    write_summary_json
    ;;
  tiny-floor)
    run_step validate_tiny python3 scripts/lab/validate_arc_tiny_gguf.py
    run_step smoke_tiny bash scripts/lab/arc_neuron_tiny_smoke.sh
    write_summary_json
    ;;
  small-build)
    run_step build_small bash scripts/operator/build_arc_neuron_small.sh
    run_step smoke_small bash scripts/lab/arc_neuron_small_smoke.sh
    write_summary_json
    ;;
  small-v2-prep)
    run_step cleanroom_exports python3 scripts/stack/build_cleanroom_supervised_exports.py
    run_step small_v2_benchmarks python3 scripts/stack/build_arc_neuron_small_v2_benchmarks.py
    run_step small_v2_prep bash scripts/operator/build_arc_neuron_small_v2_prep.sh
    write_summary_json
    ;;
  base-prep)
    run_step build_base_prep bash scripts/stack/build_arc_neuron_base_prep.sh
    write_summary_json
    ;;
  full-native-cycle)
    run_step omnibinary_language_roundtrip bash scripts/operator/run_omnibinary_bidirectional_roundtrip.sh
    run_step validate_tiny python3 scripts/lab/validate_arc_tiny_gguf.py
    run_step smoke_tiny bash scripts/lab/arc_neuron_tiny_smoke.sh
    run_step build_small bash scripts/operator/build_arc_neuron_small.sh
    run_step smoke_small bash scripts/lab/arc_neuron_small_smoke.sh
    run_step cleanroom_exports python3 scripts/stack/build_cleanroom_supervised_exports.py
    run_step small_v2_benchmarks python3 scripts/stack/build_arc_neuron_small_v2_benchmarks.py
    run_step small_v2_prep bash scripts/operator/build_arc_neuron_small_v2_prep.sh
    run_step build_base_prep bash scripts/stack/build_arc_neuron_base_prep.sh
    write_summary_json
    ;;
  *)
    echo "Unknown phase: $PHASE" >&2
    status_summary >&2
    exit 2
    ;;
esac

log "DONE phase=$PHASE reports=$REPORT_DIR"
