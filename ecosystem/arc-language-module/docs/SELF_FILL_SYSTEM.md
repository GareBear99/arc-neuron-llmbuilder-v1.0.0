# ARC Language Module Auto-Fill v1

ARC Language Module now includes a governed **self-fill** lane designed to expand the language graph without silently mutating canonical truth.

## Doctrine

The system does **not** let inference overwrite truth directly.
Instead it uses four steps:

1. **scan** the graph for missing surfaces
2. **stage** candidate rows with rationale, confidence, and provenance
3. **review / promote** candidates into canonical tables
4. **record promotion receipts** for replay and audit

This keeps the language substrate explicit while still letting it grow.

## New storage surfaces

- `self_fill_scan_runs`
- `self_fill_candidates`
- `self_fill_promotions`

## What the scanner looks for

For each language, the scanner currently checks:

- aliases present in `languages.aliases_json` but not normalized into `language_aliases`
- missing pronunciation profiles
- missing phonology profiles
- missing transliteration profiles from non-Latin scripts to Latin
- missing canonical capability rows

## Why this matters

This turns ARC Language Module into a governed multilingual substrate that can:

- find its own structural gaps
- stage repairs
- promote those repairs deliberately
- expose every step to the operator

That makes it a better truth layer for ARC-Neuron training and runtime retrieval.

## Commands

### Initialize, seed, scan

```bash
PYTHONPATH=src python scripts/run_self_fill_bootstrap.py
```

### Manual CLI flow

```bash
PYTHONPATH=src python -m arc_lang.cli.main init-db
PYTHONPATH=src python -m arc_lang.cli.main seed-common-languages
PYTHONPATH=src python -m arc_lang.cli.main self-fill-gap-scan
PYTHONPATH=src python -m arc_lang.cli.main list-self-fill-candidates --status staged --limit 20
```

### Promote one candidate

```bash
PYTHONPATH=src python -m arc_lang.cli.main promote-self-fill-candidate sfc_xxxxxxxxxxxx
```

### Reject one candidate

```bash
PYTHONPATH=src python -m arc_lang.cli.main reject-self-fill-candidate sfc_xxxxxxxxxxxx --notes "bad heuristic"
```

## Current philosophy

- **canonical truth stays explicit**
- **self-fill only stages candidates**
- **promotion creates receipts**
- **runtime capabilities stay honest**

That means the module can grow without pretending it knows more than it does.
