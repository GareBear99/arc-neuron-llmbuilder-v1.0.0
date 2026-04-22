# Self-Fill Retention Policy

This layer turns recurring self-fill releases into replayable governed release history.

It adds:
- scheduled release cycles
- retention-class assignment (`hot`, `warm`, `cold`)
- rollback index generation
- retention receipts written to SQLite
- Omnibinary/Arc-RAR artifacts preserved while release history remains queryable

## Retention classes
- `hot`: high-priority recent growth waves that should remain immediately replayable
- `warm`: accepted daily release waves with some promoted growth
- `cold`: archival waves with zero or low accepted promotion

## Operator flow
```bash
PYTHONPATH=src python scripts/run_scheduled_self_fill_release.py
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-retention-policies
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-retention-actions
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-rollback-index
```

## Why this exists
This is the first point where the language module's self-growth waves behave like governed release history instead of one-off scripts.
