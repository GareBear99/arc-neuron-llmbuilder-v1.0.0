# ARC-Core v4 Spatial Hardening Audit

## Summary

This pass moves ARC-Core from a basic geo-enabled operator seed into a more complete local spatial intelligence console with stronger evidence handling and operational authenticity.

## Major upgrades in this pass

- Added tamper-evident receipt chain with verification endpoint
- Added evidence pack export for cases or tracked subjects
- Added structure heatmap derivation from persisted tracks
- Added blueprint overlay metadata storage for floorplan alignment
- Added calibration profile storage per structure
- Added imported track ingestion endpoint for JSON-style path intake
- Added incident workflow records
- Added richer geo operator page wired to new APIs

## Why this matters

The previous build could estimate and store indoor-style tracks, but it still lacked several systems needed for a believable ARC-like operator environment:

1. **Operational provenance** — now covered by receipt chain and verification
2. **Spatial workflow continuity** — now covered by overlays, calibrations, imports, incidents
3. **Analyst exportability** — now covered by evidence pack assembly
4. **Geo pattern awareness** — now covered by heatmap generation and candidate cloud output

## Remaining gaps

- Real signed receipts and hardware-root trust are not implemented
- Real live connectors are not implemented
- Blueprint rendering is metadata-only, not full map reprojection UX
- Calibration profiles are stored, not yet actively changing estimator math
- Incident workflow is local and simple, not full multi-operator case management

## Status

ARC-Core is now materially closer to a believable deterministic ARC-style spatial intelligence kernel, while still being honest about remaining gaps versus fictional omniscience.
