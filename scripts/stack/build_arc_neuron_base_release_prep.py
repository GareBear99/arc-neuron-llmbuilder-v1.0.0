from __future__ import annotations

import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.learning_spine import LearningEvent, build_arc_rar_bundle, write_omnibinary_ledger


def count_jsonl(path: Path) -> int:
    c = 0
    if path.exists():
        with path.open('r', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    c += 1
    return c


def main() -> None:
    dataset = ROOT / 'datasets' / 'arc_neuron_base' / 'arc_neuron_base_sft.jsonl'
    gates = ROOT / 'benchmarks' / 'arc_neuron_base' / 'gate_tasks.jsonl'
    report_dir = ROOT / 'reports' / 'arc_neuron_base_release_prep'
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    contract = {
        'prepared_at': stamp,
        'model_name': 'ARC-Neuron-Base',
        'status': 'external_checkpoint_required',
        'dataset_path': str(dataset.relative_to(ROOT)),
        'dataset_records': count_jsonl(dataset),
        'gate_tasks_path': str(gates.relative_to(ROOT)),
        'gate_tasks': count_jsonl(gates),
        'operator_entrypoint': 'scripts/operator/promote_arc_neuron_base.sh',
        'external_runtime_example': 'configs/training/external_runtime.arc_neuron_base.example.yaml',
    }
    (report_dir / 'release_contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
    events = [
        LearningEvent(ts_utc=int(time.time()), source='arc_neuron_base_release_prep', event_type='release_contract_frozen', payload=contract),
    ]
    ledger = write_omnibinary_ledger(ROOT / 'artifacts' / 'omnibinary' / 'arc-neuron-base-release-prep-ledger.obin', events)
    archive = build_arc_rar_bundle(
        ROOT / 'artifacts' / 'archives' / 'arc-neuron-base-release-prep.arcrar.zip',
        [report_dir / 'release_contract.json', ROOT / contract['dataset_path'], ROOT / contract['gate_tasks_path'], ROOT / contract['external_runtime_example'], ROOT / contract['operator_entrypoint'], ROOT / 'docs' / 'ARC_NEURON_BASE_PROMOTION.md', ROOT / Path(ledger['path']).relative_to(ROOT)],
        {'kind': 'arc_neuron_base_release_prep', 'prepared_at': stamp},
    )
    out = {'ok': True, 'contract': contract, 'ledger': {'path': str(Path(ledger['path']).relative_to(ROOT)), 'sha256': ledger['sha256']}, 'archive': {'path': str(Path(archive['path']).relative_to(ROOT)), 'sha256': archive['sha256']}}
    (report_dir / 'build_result.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
