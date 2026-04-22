# v2.3 Autonomous Patch Cycle

This version extends the self-improvement subsystem from planning/scaffolding into deterministic sandbox execution.

## Added
- `lucifer self-improve apply-patch`
- `lucifer self-improve execute-cycle`
- `self_improve.executor.ImprovementExecutor`
- persisted `self_improve_patch` and `self_improve_cycle` evaluation events
- quarantine snapshots for failed promote-ready validation cycles

## Behavior
A cycle now looks like:
1. scaffold a self-improvement run
2. apply an exact line- or symbol-grounded patch in the run worktree
3. validate the run inside the worktree
4. promote if validation passes, or quarantine if configured and validation fails

The runtime still does **not** claim perfect AGI or fully autonomous open-ended self-editing. This is a deterministic, receipt-backed engineering loop extension.
