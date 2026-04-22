#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from arc_neuron_tokenizer.builder import build_tokenizer_growth_pack
from runtime.learning_spine import LearningEvent, build_arc_rar_bundle, mint_ancf_from_gguf, write_omnibinary_ledger


def main() -> None:
    import subprocess
    subprocess.run([sys.executable, str(REPO_ROOT / 'scripts' / 'stack' / 'build_cleanroom_supervised_exports.py')], check=True)
    subprocess.run([sys.executable, str(REPO_ROOT / 'scripts' / 'stack' / 'build_arc_neuron_small_v2_benchmarks.py')], check=True)
    tok = build_tokenizer_growth_pack(REPO_ROOT, vocab_target=512)

    reports = REPO_ROOT / 'reports' / 'arc_neuron_small_v2'
    artifacts_tok = REPO_ROOT / 'artifacts' / 'tokenizer'
    ancf_dir = REPO_ROOT / 'artifacts' / 'ancf'
    omni_dir = REPO_ROOT / 'artifacts' / 'omnibinary'
    arch_dir = REPO_ROOT / 'artifacts' / 'archives'
    ancf_dir.mkdir(parents=True, exist_ok=True)
    omni_dir.mkdir(parents=True, exist_ok=True)
    arch_dir.mkdir(parents=True, exist_ok=True)

    source_gguf = REPO_ROOT / 'artifacts' / 'gguf' / 'ARC-Neuron-Small-0.18M-v0.1-F32.gguf'
    ancf_path = ancf_dir / 'ARC-Neuron-Small-Prep-v0.2.ancf'
    mint_ancf_from_gguf(ancf_path, source_gguf, {
        'family': 'ARC-Neuron',
        'artifact': 'ARC-Neuron-Small-Prep-v0.2',
        'tokenizer': tok['tokenizer_path'].name,
        'benchmark_pack': 'benchmarks/arc_neuron_small_v2/gate_tasks.jsonl',
        'cleanroom_export': 'datasets/cleanroom_supervised/cleanroom_sft.jsonl',
    })

    ledger_path = omni_dir / 'arc-neuron-small-v0.2-prep-ledger.obin'
    events = [
        LearningEvent(ts_utc=0, source='tokenizer_growth', event_type='tokenizer_pack_built', payload={'vocab_size': tok['vocab_size']}),
        LearningEvent(ts_utc=0, source='cleanroom', event_type='supervised_exports_built', payload={'path': 'datasets/cleanroom_supervised/cleanroom_sft.jsonl'}),
        LearningEvent(ts_utc=0, source='benchmarks', event_type='benchmark_pack_built', payload={'path': 'benchmarks/arc_neuron_small_v2/gate_tasks.jsonl'}),
    ]
    write_omnibinary_ledger(ledger_path, events)

    archive_path = arch_dir / 'arc-neuron-small-v0.2-prep.arcrar.zip'
    build_arc_rar_bundle(archive_path, [
        tok['tokenizer_path'],
        tok['manifest_path'],
        REPO_ROOT / 'datasets' / 'cleanroom_supervised' / 'cleanroom_sft.jsonl',
        REPO_ROOT / 'datasets' / 'cleanroom_supervised' / 'cleanroom_preference.jsonl',
        REPO_ROOT / 'datasets' / 'cleanroom_supervised' / 'cleanroom_trace_receipts.jsonl',
        REPO_ROOT / 'benchmarks' / 'arc_neuron_small_v2' / 'gate_tasks.jsonl',
        ancf_path,
        ledger_path,
    ], {'family': 'ARC-Neuron', 'stage': 'Small-v0.2-prep'})

    result = {
        'status': 'ok',
        'tokenizer_path': str(tok['tokenizer_path'].relative_to(REPO_ROOT)),
        'tokenizer_manifest': str(tok['manifest_path'].relative_to(REPO_ROOT)),
        'ancf_path': str(ancf_path.relative_to(REPO_ROOT)),
        'ledger_path': str(ledger_path.relative_to(REPO_ROOT)),
        'archive_path': str(archive_path.relative_to(REPO_ROOT)),
    }
    (reports / 'arc_neuron_small_v0.2_prep_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
