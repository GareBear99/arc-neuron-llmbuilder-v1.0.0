# ARC Language Module — Production Pass Report v0.25.0

## Outcome
This pass moved the package from post-remediation beta into a stronger production-track layout.

## Completed
- Split the API surface out of the previous monolithic `src/arc_lang/api/routes.py` file into grouped routers:
  - `src/arc_lang/api/routers/core.py`
  - `src/arc_lang/api/routers/runtime.py`
  - `src/arc_lang/api/routers/knowledge.py`
  - `src/arc_lang/api/routers/acquisition.py`
- Reduced `src/arc_lang/api/routes.py` to an 11-line composition layer.
- Added `src/arc_lang/api/http.py` to centralize common HTTP error raising patterns.
- Fixed translation readiness matrix identity-pair leakage for non-identity backends.
- Tightened importer JSON parsing to catch `JSONDecodeError` explicitly instead of swallowing every exception.
- Improved Argos diagnostics to emit warnings when installed pair enumeration fails per language object.
- Added GitHub Actions CI (`.github/workflows/python-ci.yml`) for install + test validation across Python 3.10–3.12.
- Added root `.gitignore`.
- Added new regression tests for router composition, health version surface, and readiness matrix filtering.
- Bumped package/API version from `0.24.0` to `0.25.0`.

## Validation
- Full test suite passed locally.
- Current counted test functions: **330**.

## Structural effect
### Before
- `src/arc_lang/api/routes.py`: 548 lines, 86 functions

### After
- `src/arc_lang/api/routes.py`: 11 lines, 0 functions
- `src/arc_lang/api/routers/core.py`: 195 lines, 29 functions
- `src/arc_lang/api/routers/runtime.py`: 197 lines, 25 functions
- `src/arc_lang/api/routers/knowledge.py`: 169 lines, 26 functions
- `src/arc_lang/api/routers/acquisition.py`: 41 lines, 6 functions

This is materially better for authority separation, reviewability, and incremental extension.

## Remaining highest-value work
1. Split `src/arc_lang/cli/main.py` into parser-building and command-handler modules.
2. Break `src/arc_lang/services/seed_ingest.py` into manifest-specific loader units.
3. Add lint/type/static gates to CI (`ruff`, `mypy`).
4. Generate README metrics from live seeded stats at release time.
5. Add structured service-level receipts/log IDs for more mutation paths.

## Current production-track read
- Architecture: stronger than before
- Correctness: improved
- Maintainability: improved substantially on API side
- Remaining blockers: mostly maintainability / release discipline, not integrity defects
