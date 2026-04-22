# ARC Language Module v0.25.0 — Production Hardening Pass

This pass moves the package from "corrected beta" toward a more production-shaped layout.

## Completed in v0.25.0

### API authority split
- Replaced the single monolithic `src/arc_lang/api/routes.py` surface with grouped routers:
  - `api/routers/core.py`
  - `api/routers/runtime.py`
  - `api/routers/knowledge.py`
  - `api/routers/acquisition.py`
- Added `api/http.py` to centralize common HTTP error raising behavior.
- Kept `api/routes.py` as a small composition layer only.

### Runtime/diagnostics hardening
- Fixed translation readiness matrix identity-pair leakage for non-identity backends.
- Tightened import JSON parsing in `importers.py` to catch `JSONDecodeError` explicitly instead of silently swallowing all exceptions.
- Improved Argos diagnostics to emit warnings when pair enumeration fails for a specific installed language object.

### Delivery hardening
- Added GitHub Actions CI workflow for package install + full test execution across Python 3.10–3.12.
- Added root `.gitignore` for local Python/runtime artifacts.
- Added regression tests covering:
  - grouped API router composition
  - current health version surface
  - readiness matrix identity-pair skip behavior

## Current status after this pass
- Full suite passing locally.
- API surface is materially easier to extend without turning into another sink file.
- Remaining highest-value production work is mostly operational and maintainability-focused, not correctness-emergency work.

## Remaining recommended next phase
1. Split the CLI command graph into parser-building and handler modules.
2. Break `seed_ingest.py` into manifest-specific loaders.
3. Add structured logging / receipt IDs to more service-level operations.
4. Add static lint/type gates (ruff / mypy) to CI.
5. Add release automation that derives README metrics from live seeded stats.
