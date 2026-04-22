# ARC-Core v5 DARPA-Style Audit

## Executive verdict

The v4 package was functionally credible as a local operator prototype, but it still had several engineering-grade integrity gaps that would matter in a serious review. v5 closes the most important ones without pretending to solve fictional or classified-grade capabilities.

## Major findings from the line-by-line audit

### 1) Version drift
- `arc/api/main.py` and `/api/manifest` reported different effective versions.
- Fixed by introducing `arc/core/config.py` as the single version source of truth.

### 2) Weak write-path security posture
- Role gating relied only on `X-ARC-Role`.
- Fixed by adding optional `ARC_SHARED_TOKEN` / `X-ARC-Token` enforcement for non-demo write paths.

### 3) Query bounds were under-constrained
- Multiple endpoints accepted arbitrary `limit` / `grid_size` values.
- Fixed with bounded FastAPI query constraints and centralized clamping.

### 4) Search filtering happened after SQL limiting
- `/api/events?q=...` could miss relevant rows because filtering happened in Python after the DB limit.
- Fixed by pushing search predicates into SQL.

### 5) Attachment duplication risk
- Case attachments could be inserted repeatedly.
- Fixed with a unique DB index on `(case_id, event_id)` and idempotent attach behavior.

### 6) Overlay / calibration identity drift
- “upsert” behavior actually inserted new rows every time.
- Fixed with stable identity lookup and update-in-place behavior for overlays and calibration profiles.

### 7) Heatmap sampling blind spot
- Heatmap generation pulled a global tail and then filtered by structure, which could omit valid records.
- Fixed by querying track history by structure directly.

### 8) Package hygiene drift
- Redundant packaged files could drift over time.
- Fixed by packaging only the authoritative UI path and removing pycache/runtime clutter.

### 9) Data-model hardening
- The schema was permissive around duplicates and lacked identity indexes.
- Fixed with unique indexes for fingerprints, watchlist identity, structures, overlays, and calibration names.

### 10) Response consistency
- Some endpoints returned raw DB blobs without decoding JSON fields.
- Fixed for key entity/audit surfaces so the operator sees structured payloads.

## What was intentionally not faked

- no covert collection connectors
- no real-world interception claims
- no deceptive “AI certainty” layer
- no fake multi-tenant auth story
- no fabricated RF precision beyond the estimator actually implemented

## Current status

ARC-Core v5 is now a cleaner, more internally consistent, more idempotent, and more reviewable operator-grade prototype. It still needs real connectors, stronger identity fusion, proper user/session auth, and stronger signed receipts for a true next-tier build.
