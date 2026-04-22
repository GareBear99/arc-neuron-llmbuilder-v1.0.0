# Self-Fill Replay and Compaction

This layer turns scheduled language-growth waves into replayable and restorable artifacts.

## Added capabilities
- Build a replay manifest from a rollback-indexed release.
- Restore the canonical SQLite database from a release snapshot.
- Create compact Arc-RAR-style bundles for long-horizon retention.
- Record replay runs and compaction actions in SQLite.

## Operator flow
```bash
PYTHONPATH=src python scripts/run_scheduled_self_fill_release.py
PYTHONPATH=src python -m arc_lang.cli.main build-self-fill-replay-manifest --release-run-id <release_run_id>
PYTHONPATH=src python -m arc_lang.cli.main compact-self-fill-release --release-run-id <release_run_id>
PYTHONPATH=src python -m arc_lang.cli.main restore-self-fill-snapshot --release-run-id <release_run_id>
```

## Notes
- Every self-fill release now captures a snapshot of `data/arc_language.db`.
- Restores create a backup copy by default before replacing the live database.
- Compaction bundles preserve the manifest, ledger, and snapshot while reducing archive scope for colder retention classes.
