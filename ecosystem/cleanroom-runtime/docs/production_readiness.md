# Production Readiness Gate

Current package state: **v2.11.2**

This repo now clears the following local release gates:

- `pytest -q`
- `bash scripts/smoke.sh`
- `bash scripts/release_check.sh`
- `python scripts/version_audit.py`
- `python -m lucifer_runtime.cli --workspace . doctor --release-gate --strict`
- `python scripts/soak.py --workspace . --iterations 10 --output artifacts/soak_receipt.json`

## What changed in the v2.11.x hardening passes

- Version truth was aligned across package metadata, README, changelog, and built artifacts.
- Candidate validation command execution was hardened away from `shell=True`.
- Missing release hygiene files were added so the public repo surface matches the claims in the docs.
- The CLI entrypoint was decomposed into separate parser, handler, and dispatch modules.

## Current honest status

This repository is now a **credible production-ready local release candidate** for:

- deterministic operator workflows
- local runtime persistence and continuity
- FixNet / trust / curriculum / directive flows
- self-improvement scaffolding and validation loops
- repo distribution with repeatable release checks
- CI-enforced release hygiene and deterministic soak receipts

It is **not** yet proven for:

- long-duration autonomous soak on the user's exact hardware
- signed installer / notarized end-user desktop distribution
- validated safety under unrestricted external command/plugin ecosystems
- fully decomposed runtime authority inside `runtime.py`

## Remaining highest-value next steps

1. Split `src/lucifer_runtime/runtime.py` into smaller authority modules.
2. Add signed release packaging and installer docs per target platform.
3. Add long-run soak scripts and benchmark receipts for real GGUF/model combos.
4. Add stricter structured receipts around degraded/fallback paths.
