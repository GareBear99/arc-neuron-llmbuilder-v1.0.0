# Ingestion Plan — Current State (v0.24)

This document describes the complete ingestion architecture as it exists now.

## Ingestion doctrine

- No single source owns universal truth. Every imported record carries provenance with source name, source ref, and confidence weight.
- Glottolog-style inputs populate genealogical structure (family/branch nodes, lineage edges).
- ISO 639-3-style inputs normalize authoritative identifiers and add aliases.
- CLDR-style inputs populate script mappings and display-name aliases.
- Custom lineage assertions are tracked separately from source-backed edges and participate in arbitration.
- When an imported record collides with an existing custom lineage assertion, the collision is logged in the import result `conflicts` list — it is never silently overwritten.
- Provenance records are attached to every imported language row, lineage node, and lineage edge.

## Supported file formats

| Format | Source style | CLI command | API route |
|--------|-------------|-------------|-----------|
| CSV | Glottolog genealogy | `import-glottolog-fixture <path> [--dry-run]` | `POST /import/glottolog?dry_run=true` |
| CSV | ISO 639-3 identifiers | `import-iso-fixture <path> [--dry-run]` | `POST /import/iso639_3?dry_run=true` |
| JSON | CLDR locales/scripts | `import-cldr-fixture <path> [--dry-run]` | `POST /import/cldr?dry_run=true` |

### dry_run mode

All three importers support `dry_run=True`. In dry-run mode: all rows are parsed and validated, conflict detection runs, no rows are written, no import_run receipt is recorded. The returned dict includes `dry_run: true`, `records_seen`, `records_inserted: 0`, `records_updated: 0`, `conflict_count`, and `conflicts`.

### Dedup reporting

Live imports return separate `records_inserted` and `records_updated` counters.

## Import order (recommended)

1. `init-db` — initialize schema
2. `seed-common-languages` — bootstrap 35 languages, 14 families, providers, manifests, phonology/transliteration profiles
3. `import-glottolog-fixture <path>` — genealogical structure
4. `import-iso-fixture <path>` — authoritative ISO codes and aliases
5. `import-cldr-fixture <path>` — script mappings and aliases

Steps 3-5 are idempotent.

## Real corpus acquisition (external gap — honest)

| Corpus | Acquisition status | License |
|--------|-------------------|---------|
| Glottolog (glottolog.org) | external_required | CC Attribution 4.0 |
| ISO 639-3 (SIL) | external_required | Free non-commercial |
| CLDR (Unicode) | external_required | Unicode License |

Use the acquisition workspace CLI to track staging:

```
python -m arc_lang.cli.main plan-acquisition-job Glottolog --stage-name staging
python -m arc_lang.cli.main validate-staged-asset <file_path> csv
python -m arc_lang.cli.main export-ingestion-workspace workspace_export.json
```

## Source authority weights

| Source | Weight |
|--------|--------|
| iso639_3 | 0.9 |
| glottolog | 1.0 |
| cldr | 0.85 |
| common_seed | 0.6 |
| common_seed_local | 0.7 |
| user_submission | 0.45 |
| user_custom | 0.6 |

Update at runtime: `set-source-weight <source_name> <weight>`
