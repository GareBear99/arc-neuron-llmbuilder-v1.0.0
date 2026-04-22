#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH=src

python -m lucifer_runtime.cli commands >/dev/null
python -m lucifer_runtime.cli write smoke.txt "hello from smoke" >/dev/null
python -m lucifer_runtime.cli read smoke.txt >/dev/null
python -m lucifer_runtime.cli state >/dev/null
python -m lucifer_runtime.cli info >/dev/null
python -m lucifer_runtime.cli doctor >/dev/null
python -m lucifer_runtime.cli bench >/dev/null
python -m lucifer_runtime.cli self-improve analyze >/dev/null
python -m lucifer_runtime.cli trace --output smoke_trace.html >/dev/null

echo "smoke ok"
python -m lucifer_runtime.cli robot describe >/dev/null
python -m lucifer_runtime.cli mapping state-template >/dev/null
python -m lucifer_runtime.cli spatial state-template >/dev/null
python -m lucifer_runtime.cli geo anchor-template >/dev/null
python -m lucifer_runtime.cli bt describe >/dev/null

python -m lucifer_runtime.cli bt signal-observation --devices-json '[{"device_id":"garage.main","display_name":"Main Garage Relay","profile":"garage_relay_profile","trusted":true,"pairing_state":"paired","ownership":"owned","signal_kind":"ble","last_seen_rssi":-50,"metadata":{"zone":"garage"}}]' --device-id garage.main >/dev/null
python -m lucifer_runtime.cli spatial ingest-bt-signal --state-json '{"anchors":[],"observations":[],"confidence_world":{}}' --signal-json '{"device_id":"garage.main","display_name":"Main Garage Relay","profile":"garage_relay_profile","trusted":true,"pairing_state":"paired","ownership":"owned","signal_kind":"ble","last_seen_rssi":-50,"metadata":{"zone":"garage"}}' >/dev/null
