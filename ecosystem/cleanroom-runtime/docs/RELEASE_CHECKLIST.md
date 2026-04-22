# Release Checklist

Use this checklist before marking a build as a public release candidate.

## Mandatory local gates

- `python -m pip install -e .[dev]`
- `python scripts/version_audit.py`
- `pytest -q`
- `bash scripts/smoke.sh`
- `bash scripts/release_check.sh`
- `python -m lucifer_runtime.cli --workspace . doctor --release-gate --strict`
- `python scripts/soak.py --workspace . --iterations 10 --output artifacts/soak_receipt.json`

## Required review points

- README, docs, and package version all agree.
- Protected-core self-improvement paths still block unsafe promotion.
- Release artifacts do not contain stale versioned builds.
- Optional adapters are still labeled as optional/bounded rather than implied as universal live capability.
- The current branch can produce a deterministic soak receipt without silent failures.

## Still outside repo-only completion

- Hardware-specific model benchmarking
- Signed installer / notarization flow
- Real BLE / robotics device validation on target machines
- Multi-day autonomy proof on the final hardware and model combination
