# Approved Self-Fill Importers

This layer adds governed source importers on top of the self-fill staging system.

## Purpose
Approved importers do **not** write directly into canonical truth. They:
- parse approved fixture/source formats
- stage self-fill candidates
- write import-run receipts
- record conflicts for review
- preserve explicit promotion lanes

## Included importer lanes
- ISO 639 fixture -> alias candidates
- Glottolog fixture -> lineage coverage capability candidates
- CLDR fixture -> transliteration bridge candidates

## Commands
```bash
PYTHONPATH=src python -m arc_lang.cli.main stage-iso-self-fill examples/iso6393_sample.csv
PYTHONPATH=src python -m arc_lang.cli.main stage-glottolog-self-fill examples/glottolog_sample.csv
PYTHONPATH=src python -m arc_lang.cli.main stage-cldr-self-fill examples/cldr_sample.json
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-import-runs --limit 20
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-conflicts --limit 20
PYTHONPATH=src python -m arc_lang.cli.main resolve-self-fill-conflict <conflict_id> accepted
```

## Bootstrap
```bash
PYTHONPATH=src python scripts/run_approved_self_fill_bootstrap.py
```

The bootstrap runs all example importers and writes a JSON report to `docs/approved_self_fill_bootstrap_report.json`.

## Current doctrine
- canonical graph remains explicit
- imported candidates remain staged until promoted
- conflicts are first-class review objects
- import runs emit durable receipts
- self-fill stays additive and auditable
