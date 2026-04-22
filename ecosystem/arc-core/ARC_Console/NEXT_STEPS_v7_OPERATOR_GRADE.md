# ARC-Core v7 Next Steps

## Highest-value build targets

### 1) Real connector adapters
- Add pluggable adapters for REST pull, webhook intake, email/IMAP parsing, CSV drops, and sensor streams.
- Normalize all inbound records into the canonical event schema before persistence.

### 2) Strong identity fusion
- Add multi-signal entity matching using names, aliases, devices, locations, fingerprints, and confidence decay.
- Surface merge proposals instead of auto-merging low-confidence identities.

### 3) Asymmetric receipt signing
- Replace local HMAC receipts with asymmetric signing and key rotation metadata.
- Add exportable verification manifests.

### 4) Worker separation
- Split API, connector polling, and enrichment into separate worker roles.
- Add retry semantics, dead-letter queue behavior, and bounded backpressure.

### 5) Analyst workflow polish
- Add notebook UI, saved searches, evidence bundles, incident summaries, and case timelines.
- Add CSV/JSON/PDF export later if needed.

### 6) Spatial fidelity upgrades
- Add floorplan image overlays, calibration points, track smoothing, confidence ellipses, and better RF/anchor modeling.

### 7) Real auth/RBAC hardening
- Move from demo bootstrap/session flow to real user management, password hashing policy controls, and action-scoped permissions.

## Suggested implementation order
1. Connectors
2. Identity fusion
3. Receipt signing
4. Worker split
5. Analyst workflow
6. Spatial fidelity
7. Full RBAC hardening
