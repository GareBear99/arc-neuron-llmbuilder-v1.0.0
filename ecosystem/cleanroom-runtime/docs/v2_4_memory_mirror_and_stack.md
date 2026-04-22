# v2.4 memory mirror + stacked readability

This upgrade adds early archive mirroring with live front-memory retention.

## Key behavior
- `memory archive-now <event_id>` mirrors a record into the archive branch early.
- The original record stays live in front memory until its scheduled archive date.
- `memory sync` refreshes mirrored live records into the archive branch.
- Consolidation retires live memory at the scheduled archive date and records that retirement date.

## Readable memory headers
Memory records now carry:
- title
- summary
- keywords
- category
- importance
- status

This gives the runtime a more SEO-like stacked memory shape for retrieval and inspection.
