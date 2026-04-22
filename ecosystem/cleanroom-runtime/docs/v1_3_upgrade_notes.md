# v1.3 Upgrade Notes

This version adds a memory-retention subsystem with three tiers:

- hot live memory
- warm indexed memory
- immutable `.arcpack` archive bundles

## Added

- `memory_subsystem/records.py`
- `memory_subsystem/retention.py`
- `memory_subsystem/archive.py`
- `memory_subsystem/manager.py`
- `examples/run_memory_retention.py`
- `docs/memory_retention.md`

## Kernel integration

The ARC kernel now records `memory_update` events and projects archive manifests into state.

## Policy

Default archival threshold: 180 days, except pinned or recently-accessed records.
