# v1.4.2 Persistence Fix

- CLI now persists to a workspace-local SQLite database by default at `.arc_lucifer/events.sqlite3`.
- `write`, `read`, `state`, and `trace` now share the same kernel history across separate CLI invocations without requiring `--db`.
- Added regression coverage for state persistence and trace rendering against the default workspace database.
