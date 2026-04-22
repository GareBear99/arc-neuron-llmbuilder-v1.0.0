# v0.4 Upgrade Notes

This upgrade hardens the clean-room runtime beyond scaffold level.

## Added
- Resumable pending confirmations by `proposal_id`
- Operator-side approve/reject flow without reparsing the original intent
- Receipt-driven rollback for file writes and deletes
- Replayable state projection at a specific receipt event
- Derived pending/completed/denied proposal state
- Backend registry for model service wiring

## Why it matters
The runtime now behaves more like an auditable control system:
- actions can pause and resume
- destructive mutations can be rolled back
- state can be replayed at a precise historical boundary
- policy status is derived from the event ledger instead of ad hoc flags

## Remaining gaps before a larger production push
- richer shell sandboxing and command budget policy
- multi-artifact rollback bundles
- persistent branch-scoring history
- evaluator loop with regression scoring
- interactive dashboard instead of static trace HTML
- pluggable real local backends (llamafile / llama.cpp / vLLM)
