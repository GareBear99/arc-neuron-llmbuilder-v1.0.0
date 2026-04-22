# ADR 0003: Cache integrity before speed

## Status
Accepted

## Decision
Persistent caches must encode compatibility metadata, invalidation conditions, and version boundaries before they are trusted for acceleration.

## Rationale
Corrupt or stale translated artifacts are worse than cold execution.
