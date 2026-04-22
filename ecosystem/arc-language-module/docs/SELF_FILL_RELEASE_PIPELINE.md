# Self-Fill Release Pipeline

This layer turns approved self-fill growth into a governed release event.

## What it does
- runs gap scan
- runs approved importer staging
- runs authority arbitration
- promotes winning candidates
- writes a signed manifest
- writes an Omnibinary-style binary ledger (`.obin`)
- writes an Arc-RAR-style archive bundle (`.arcrar.zip`)
- records release artifacts in SQLite

## Signature model
- If `ARC_LANG_SIGNING_KEY` is provided, manifests are signed with `hmac-sha256`.
- If no key is provided, the system emits a deterministic `sha256-integrity-only` signature payload.

## Operator flow
```bash
PYTHONPATH=src python scripts/run_recurring_self_fill_release.py
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-release-runs
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-release-artifacts
```

## Artifact layout
- `artifacts/release_manifests/*.manifest.json`
- `artifacts/release_manifests/*.manifest.sig.json`
- `artifacts/omnibinary/*.obin`
- `artifacts/archives/*.arcrar.zip`

## Intent
This is the first point where accepted language growth is treated as:
- a governed promotion wave
- a signed release receipt
- a binary ledger event
- an archival rollback bundle
