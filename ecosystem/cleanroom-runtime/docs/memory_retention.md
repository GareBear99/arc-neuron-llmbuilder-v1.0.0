# Memory Retention and Archive Packs

This runtime now separates living memory from long-horizon archive packs.

## Tiers

- **Hot**: recent records that should stay fast and directly queryable.
- **Warm**: medium-age records that still stay indexed locally in `warm/warm_index.json`.
- **Archive**: immutable `.arcpack` bundles for older records that no longer belong in the hot working set.

## Default policy

- Hot: 30 days
- Warm: 31 to 180 days
- Archive: older than 180 days, unless pinned or recently accessed

Archiving is controlled by both age and relevance. Records are **not** archived when they are pinned or when `last_accessed_at` is still inside the access grace window.

## Archive pack format

Each `.arcpack` is a zip-compressed immutable bundle containing:

- `manifest.json`
- `events.jsonl`

The manifest includes:

- record count
- first and last timestamps
- event ids
- payload sha256

## Longevity math

Storage requirement is approximately:

`events_per_day * average_event_size * days`

Examples with 4:1 archive compression:

- 2,000 events/day at 1 KB raw/event → ~0.18 GB per year archived
- 10,000 events/day at 1 KB raw/event → ~0.87 GB per year archived
- 10,000 events/day at 4 KB raw/event → ~3.48 GB per year archived

At those rates, 50 years of history remains practical as long as the system keeps the hot tier small and seals old data into immutable packs.

## Runtime integration

`MemoryManager` can be run periodically to:

1. classify records into hot/warm/archive
2. write the warm index
3. seal old records into `.arcpack` bundles
4. emit a `memory_update` event back into the ARC kernel
