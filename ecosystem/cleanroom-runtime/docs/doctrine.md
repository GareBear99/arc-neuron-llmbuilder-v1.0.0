# Doctrine

## Core rules

1. The model never directly acts.
2. Every meaningful action becomes an event.
3. State is derived from receipts and events.
4. Destructive actions require confirmation.
5. Unknown intents are denied by default.
6. Workspaces are explicit boundaries.
7. Execution without validation is incomplete.

## v0.3 hardening additions

- SQLite persistence establishes replayable authority.
- Branch planning happens before execution, even in simple form.
- Workspace-bound filesystem adapters prevent path escape.
- Shell execution is explicitly allowlisted.
- Trace export makes post-action auditing human-readable.
