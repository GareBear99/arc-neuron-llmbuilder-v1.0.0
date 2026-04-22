# v1.7 Production Hardening

Adds production-oriented operational features:

- Default workspace-local config discovery at `.arc_lucifer/config.json`
- `lucifer config show` and `lucifer config init`
- `lucifer doctor` diagnostics for Python, workspace, DB, PATH, and llamafile assets
- `lucifer export --jsonl ... --sqlite-backup ...` for backup and portability
- SQLite durability tuning via WAL, busy timeout, and normal sync mode
- Shared default DB remains `.arc_lucifer/events.sqlite3`
