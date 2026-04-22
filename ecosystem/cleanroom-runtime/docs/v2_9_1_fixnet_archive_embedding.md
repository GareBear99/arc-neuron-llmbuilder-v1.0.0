# v2.9.1 FixNet archive embedding

This upgrade adds a first-class FixNet dossier lane so repair intelligence can be persisted into the same branch-visible history as ARC/Lucifer runtime events.

## What changed

- Added `fixnet record` to create structured fix dossiers.
- Added `fixnet embed` to write embedded archive packs under `.arc_lucifer/fixnet/embedded_archive/`.
- State projection now exposes:
  - `fixnet_cases`
  - `fixnet_archives`
  - `world_model.fixnet_case_count`
  - `world_model.fixnet_archive_count`
- Embedded FixNet archives are recorded both as evaluation events and memory updates so the archive-visible branch state can see the same evidence trail.

## Why this matters

Previously, self-improvement events were recorded in the event spine, while richer repair context could remain stranded in local worktree artifacts. This closes that gap by giving FixNet its own persisted evidence channel.

## Example

```bash
PYTHONPATH=src python -m lucifer_runtime.cli fixnet record \
  --title "Promotion failure dossier" \
  --summary "Consensus repair evidence for a failed promotion attempt." \
  --keywords "fixnet,promotion,self-improve" \
  --quality-grade "grade-11" \
  --linked-run-id run-123

PYTHONPATH=src python -m lucifer_runtime.cli fixnet embed <case_id> \
  --archive-branch-id archive_branch_main \
  --include-json '{"source":"self_improve"}'
```

The result is a durable embedded archive artifact plus matching state/history entries.
