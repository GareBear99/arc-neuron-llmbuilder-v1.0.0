from __future__ import annotations
from pathlib import Path
import json, csv


def count_jsonl(path: Path) -> int:
    n = 0
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                json.loads(line)
                n += 1
    return n


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = root / 'manifests' / 'omnibinary_source_manifest.csv'
    with manifest.open('r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    sft = count_jsonl(root / 'datasets/distillation_sft/omnibinary_seed_records.jsonl')
    pref = count_jsonl(root / 'datasets/distillation_preference/omnibinary_seed_pairs.jsonl')
    ev = count_jsonl(root / 'datasets/distillation_eval/omnibinary_seed_tasks.jsonl')
    report = {
        'manifest_rows': len(rows),
        'sft_records': sft,
        'preference_pairs': pref,
        'eval_tasks': ev,
        'status': 'ok'
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
