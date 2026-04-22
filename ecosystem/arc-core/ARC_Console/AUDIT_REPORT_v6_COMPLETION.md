# ARC-Core v6 Completion Audit

## Summary

v6 closes the largest remaining gaps from the prior DARPA-style review by adding four missing system layers that materially improve authenticity and operator credibility:

1. **Local auth + sessions**
2. **Signed receipt verification**
3. **Connector bus with ingest polling**
4. **Analyst notebook / enriched evidence export**

## What changed

### 1) Auth/session model
- Added `auth_users` and `auth_sessions` tables.
- Added bootstrap admin creation.
- Added password hashing via PBKDF2.
- Added `/api/auth/bootstrap`, `/api/auth/login`, and `/api/auth/session`.
- Added bearer-session aware role checks so routes can authorize from a session token instead of only trusting a raw role header.

### 2) Signed receipts
- Extended `receipt_chain` with `signature` and `key_id`.
- Added local signing key persistence under `data/keys/`.
- Added deterministic HMAC signing for each receipt payload.
- Updated receipt verification to validate both chain integrity and signatures.

### 3) Connector bus
- Added `connector_sources` and `connector_runs` tables.
- Added local `filesystem_jsonl` connector adapter.
- Added connector poll workflow and run history.
- Added demo feed bootstrap so the package has a live-ish deterministic source on first run.

### 4) Analyst notebook + evidence enrichment
- Added `analyst_notes` table.
- Added note creation and lookup endpoints.
- Enriched evidence exports with entities, edges, summary metrics, and notes.
- Improved event search to match entity labels in addition to internal entity IDs.

## Operational reality check

This is now a stronger operator-grade local prototype, but it still is not a literal ARC from fiction.

Still missing for a deeper next tier:
- real connectors beyond filesystem polling
- strong identity fusion across heterogeneous sources
- distributed workers / queueing / backpressure
- hardened multi-user UI flows
- hardware-backed or asymmetric signing
- validated real-world RF and geospatial models

## Validation

- `13 passed`

## Final assessment

v6 is the first version in this chain that has a coherent answer for:
- who can act
- how actions are sessioned
- how outside data enters the system
- how evidence is annotated
- how receipts are signed and verified

That makes it substantially closer to a believable ARC-style operator kernel than the earlier scaffold-centric builds.
