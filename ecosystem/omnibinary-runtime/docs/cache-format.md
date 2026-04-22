# Cache Format

Current cache layout:

```text
~/.cache/omnibinary/
  inspects/
  runs/
  doctor/
  index/
    receipts.jsonl
```

Current guarantees:
- JSON receipts are persisted per category.
- An append-only `receipts.jsonl` index tracks recent writes.

Not yet implemented:
- compiled block caches
- artifact compatibility stamps
- cache eviction policy
- versioned invalidation for translated code
