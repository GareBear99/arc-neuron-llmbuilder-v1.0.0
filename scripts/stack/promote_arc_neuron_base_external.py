from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.learning_spine import LearningEvent, build_arc_rar_bundle, mint_ancf_from_gguf, write_omnibinary_ledger


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    payload = {
        'command': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }
    if proc.returncode != 0:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def latest_gguf(candidate: str) -> Path:
    gguf_dir = ROOT / 'exports' / 'candidates' / candidate / 'gguf_export'
    options = sorted(gguf_dir.glob('*.gguf'))
    if not options:
        raise FileNotFoundError(f'No GGUF files found in {gguf_dir}')
    return max(options, key=lambda p: p.stat().st_mtime)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', default='arc-neuron-base')
    ap.add_argument('--base-model', required=True)
    ap.add_argument('--dataset', default=str(ROOT / 'datasets' / 'arc_neuron_base' / 'arc_neuron_base_sft.jsonl'))
    ap.add_argument('--mode', choices=['scaffold', 'external'], default='external')
    ap.add_argument('--model-name', default='ARC-Neuron-Base')
    ap.add_argument('--version', default='v1.0')
    args = ap.parse_args()

    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    run_dir = ROOT / 'reports' / 'arc_neuron_base_release' / f'{args.candidate}_{stamp}'
    run_dir.mkdir(parents=True, exist_ok=True)

    stages = []
    stage_cmds = [
        ['python3', 'scripts/training/train_lora_candidate.py', '--candidate', args.candidate, '--base-model', args.base_model, '--dataset', args.dataset, '--mode', args.mode],
        ['python3', 'scripts/training/merge_adapters_stub.py', '--candidate', args.candidate, '--base-model', args.base_model, '--mode', args.mode],
        ['python3', 'scripts/training/export_gguf_candidate.py', '--candidate', args.candidate, '--mode', args.mode],
    ]
    for cmd in stage_cmds:
        stages.append(run(cmd))

    gguf_path = latest_gguf(args.candidate)
    release_name = f"{args.model_name}-{args.version}-{stamp}"
    gguf_release = ROOT / 'artifacts' / 'gguf' / f'{release_name}.gguf'
    gguf_release.parent.mkdir(parents=True, exist_ok=True)
    gguf_release.write_bytes(gguf_path.read_bytes())

    events = [
        LearningEvent(ts_utc=int(time.time()), source='arc_neuron_base_release', event_type='promotion_started', payload={'candidate': args.candidate, 'base_model': args.base_model}),
        LearningEvent(ts_utc=int(time.time()), source='arc_neuron_base_release', event_type='dataset_bound', payload={'dataset': args.dataset}),
        LearningEvent(ts_utc=int(time.time()), source='arc_neuron_base_release', event_type='gguf_exported', payload={'gguf': str(gguf_release.relative_to(ROOT))}),
    ]
    ledger = write_omnibinary_ledger(ROOT / 'artifacts' / 'omnibinary' / 'arc-neuron-base-release-ledger.obin', events)

    ancf = mint_ancf_from_gguf(
        ROOT / 'artifacts' / 'ancf' / f'{release_name}.ancf',
        gguf_release,
        {
            'model_name': args.model_name,
            'version': args.version,
            'candidate': args.candidate,
            'base_model': args.base_model,
            'dataset': args.dataset,
            'release_stamp': stamp,
            'ledger_path': ledger['path'],
            'benchmark_gate_tasks': 'benchmarks/arc_neuron_base/gate_tasks.jsonl',
        },
    )

    archive_manifest = {
        'model_name': args.model_name,
        'version': args.version,
        'candidate': args.candidate,
        'base_model': args.base_model,
        'dataset': args.dataset,
        'stamp': stamp,
        'gguf': str(gguf_release.relative_to(ROOT)),
        'ancf': os.path.relpath(ancf['path'], ROOT),
        'ledger': os.path.relpath(ledger['path'], ROOT),
    }
    archive = build_arc_rar_bundle(
        ROOT / 'artifacts' / 'archives' / 'arc-neuron-base-release.arcrar.zip',
        [gguf_release, ROOT / os.path.relpath(ancf['path'], ROOT), ROOT / os.path.relpath(ledger['path'], ROOT)],
        archive_manifest,
    )

    report = {
        'ok': True,
        'candidate': args.candidate,
        'model_name': args.model_name,
        'version': args.version,
        'stamp': stamp,
        'stages': stages,
        'artifacts': {
            'gguf': str(gguf_release.relative_to(ROOT)),
            'ancf': os.path.relpath(ancf['path'], ROOT),
            'omnibinary_ledger': os.path.relpath(ledger['path'], ROOT),
            'archive_bundle': os.path.relpath(archive['path'], ROOT),
        },
    }
    (run_dir / 'promotion_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
