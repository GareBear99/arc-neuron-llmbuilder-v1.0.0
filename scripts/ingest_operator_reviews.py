#!/usr/bin/env python3
"""Pull live-deployment reviews from gh-ai-operator into LLMBuilder's corpus.

gh-ai-operator emits one JSONL record per live review in the seed-examples
schema LLMBuilder already uses at
`data/<capability>/seed_examples.jsonl`.

This script:
  1.  Reads JSONL from either:
        (a) a local directory (e.g. a downloaded artifact), or
        (b) an arbitrary list of files/globs,
      defaulting to `./_operator_exports/training_export/critique/*.jsonl`.
  2.  Deduplicates by `id` against the existing corpus shard.
  3.  Weights records tagged `correction` above vanilla live-deployment
      records (correction confidence +0.05, capped at 1.0).
  4.  Writes the merged result into
      `data/critique/operator_reviews.jsonl` — kept separate from
      `seed_examples.jsonl` so a human can still diff / curate before
      promoting ingested records into the canonical seed file.
  5.  Prints a manifest summary (counts, last-seen SHA, top tags).

Usage:

    # 1. Download the latest gh-ai-operator artifact (or use `gh run download`)
    gh run download <run-id> -R GareBear99/gh-ai-operator \
      -n llmbuilder-training-export -D _operator_exports

    # 2. Ingest
    python scripts/ingest_operator_reviews.py

    # 3. Inspect + promote
    head data/critique/operator_reviews.jsonl
    # optionally merge curated rows into data/critique/seed_examples.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_GLOB = str(
    ROOT / '_operator_exports' / 'training_export' / 'critique' / '*.jsonl'
)
DEFAULT_OUTPUT = ROOT / 'data' / 'critique' / 'operator_reviews.jsonl'

REQUIRED_FIELDS = {
    'id', 'capability', 'domain', 'difficulty', 'input', 'target', 'tags',
}


def load_jsonl(paths: Iterable[Path]) -> List[Dict]:
    records: List[Dict] = []
    for p in paths:
        if not p.exists():
            continue
        with p.open('r', encoding='utf-8') as fh:
            for i, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f'[warn] {p}:{i} invalid JSON: {exc}', file=sys.stderr)
                    continue
                if not isinstance(obj, dict):
                    continue
                records.append(obj)
    return records


def validate(rec: Dict) -> bool:
    if not REQUIRED_FIELDS.issubset(rec.keys()):
        return False
    if rec.get('capability') != 'critique':
        return False
    if not isinstance(rec.get('input'), dict) or 'task' not in rec['input']:
        return False
    if not isinstance(rec.get('target'), dict) or 'analysis' not in rec['target']:
        return False
    return True


def dedupe_and_weight(records: List[Dict]) -> List[Dict]:
    """Keep the latest record per `id`. Bump correction confidence by +0.05."""
    by_id: Dict[str, Dict] = {}
    for rec in records:
        rid = rec.get('id')
        if not rid:
            continue
        if 'correction' in (rec.get('tags') or []):
            conf = rec.get('target', {}).get('confidence', 0.75)
            try:
                conf = min(1.0, float(conf) + 0.05)
                rec['target']['confidence'] = conf
            except (TypeError, ValueError):
                pass
        by_id[rid] = rec  # last wins
    return list(by_id.values())


def write_jsonl(records: List[Dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False))
            fh.write('\n')


def print_manifest(records: List[Dict], out: Path) -> None:
    tag_counts: Counter = Counter()
    diff_counts: Counter = Counter()
    verdict_counts: Counter = Counter()
    for rec in records:
        for t in rec.get('tags') or []:
            tag_counts[t] += 1
        diff_counts[rec.get('difficulty', 'unknown')] += 1
        v = (rec.get('target') or {}).get('verdict') or 'n/a'
        verdict_counts[v] += 1
    print(f'[ingest] wrote {len(records)} records -> {out}')
    print(f'[ingest] difficulty: {dict(diff_counts)}')
    print(f'[ingest] verdict:    {dict(verdict_counts)}')
    print(f'[ingest] top tags:   {tag_counts.most_common(8)}')


def main() -> int:
    ap = argparse.ArgumentParser(description='Ingest gh-ai-operator reviews into LLMBuilder.')
    ap.add_argument(
        '--inputs', nargs='*',
        help='JSONL file(s) or glob(s). Default: ./_operator_exports/training_export/critique/*.jsonl',
    )
    ap.add_argument(
        '--out', default=str(DEFAULT_OUTPUT),
        help='Output JSONL shard (default: data/critique/operator_reviews.jsonl).',
    )
    ap.add_argument(
        '--strict', action='store_true',
        help='Exit non-zero if any record fails validation.',
    )
    args = ap.parse_args()

    # Resolve inputs
    if args.inputs:
        input_paths: List[Path] = []
        for pat in args.inputs:
            input_paths.extend(Path().glob(pat))
    else:
        input_paths = list(Path().glob(DEFAULT_INPUT_GLOB))

    if not input_paths:
        print('[ingest] no inputs found. Provide --inputs or drop files into '
              f'{DEFAULT_INPUT_GLOB}', file=sys.stderr)
        return 0

    raw = load_jsonl(input_paths)
    valid: List[Dict] = []
    bad = 0
    for rec in raw:
        if validate(rec):
            valid.append(rec)
        else:
            bad += 1
    if bad:
        msg = f'[ingest] skipped {bad} records that failed schema validation.'
        print(msg, file=sys.stderr)
        if args.strict:
            return 2

    merged = dedupe_and_weight(valid)
    out = Path(args.out)
    write_jsonl(merged, out)
    print_manifest(merged, out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
