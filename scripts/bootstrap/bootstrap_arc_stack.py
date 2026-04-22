from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES = {
    'cleanroom': Path('/mnt/data/arc-lucifer-cleanroom-runtime-main (16).zip'),
    'arc_core': Path('/mnt/data/ARC-Core-main (18).zip'),
    'omnibinary': Path('/mnt/data/omnibinary-runtime-main (1).zip'),
    'arc_rar': Path('/mnt/data/Arc-RAR-main (3).zip'),
    'language_module': Path('/mnt/data/arc-language-module-main (4).zip'),
}
OPTIONAL_SOURCES = {
    'turbo_os': Path('/mnt/data/ARC-Turbo-OS-main (2).zip'),
}


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        'cmd': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_env_template(output_dir: Path, candidate: str, base_model_ref: str) -> Path:
    out = output_dir / 'real_gguf_build.env.bootstrap'
    fp16 = output_dir / f'{candidate}-f16.gguf'
    quant = output_dir / f'{candidate}-q4_k_m.gguf'
    llamafile = output_dir / f'{candidate}.llamafile'
    lines = [
        '# Generated bootstrap env. Replace placeholder toolchain/model paths with real absolute paths.',
        f'FLAGSHIP_MODEL_NAME={candidate}',
        'FLAGSHIP_VERSION=0.1.0-bootstrap',
        f'MODEL_FAMILY={base_model_ref}',
        'PROMPT_PROFILE=flagship',
        'MAX_CONTEXT_TOKENS=8192',
        f'COGNITION_CANDIDATE_ID={candidate}',
        'COGNITION_BASE_MODEL_DIR=/absolute/path/to/base_model_dir',
        'COGNITION_MERGED_MODEL_DIR=/absolute/path/to/merged_model_dir',
        'COGNITION_CONVERT_SCRIPT=/absolute/path/to/llama.cpp/convert_hf_to_gguf.py',
        'COGNITION_CONVERT_EXTRA_ARGS=',
        'COGNITION_QUANTIZE_BIN=/absolute/path/to/llama.cpp/build/bin/llama-quantize',
        'COGNITION_RUNTIME_BINARY=/absolute/path/to/llama.cpp/build/bin/llama-cli',
        'COGNITION_PYTHON_BIN=python3',
        'COGNITION_QUANT_TYPE=Q4_K_M',
        f'COGNITION_FP16_MODEL_FILE={fp16}',
        f'COGNITION_QUANTIZED_MODEL_FILE={quant}',
        '# Optional: shell command that produces the merged model directory.',
        'COGNITION_MERGE_COMMAND=',
        'BUILD_LLAMAFILE=1',
        'COGNITION_LLAMAFILE_BINARY=/absolute/path/to/llamafile',
        f'COGNITION_LLAMAFILE_FILE={llamafile}',
    ]
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description='Bootstrap cognition-core from the uploaded ARC stack and prepare a first GGUF handoff.')
    ap.add_argument('--candidate', default='arc_stack_bootstrap')
    ap.add_argument('--base-model', default='qwen3_32b_lora')
    ap.add_argument('--mode', choices=['auto', 'scaffold', 'external'], default='scaffold')
    ap.add_argument('--output-dir', default=str(ROOT / 'reports' / 'bootstrap_arc_stack'))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    steps: list[dict] = []

    steps.append(run([sys.executable, 'scripts/execution/run_training_readiness_gate.py']))
    steps.append(run([sys.executable, 'scripts/training/prepare_distillation_corpus.py']))

    for package, source in DEFAULT_SOURCES.items():
        if not source.exists():
            steps.append({
                'cmd': ['missing_source', package, str(source)],
                'returncode': 2,
                'stdout': '',
                'stderr': f'Missing expected source archive: {source}',
            })
            continue
        steps.append(run([
            sys.executable,
            'scripts/build_supporting_repo_corpus.py',
            '--source',
            str(source),
            '--package',
            package,
            '--limit',
            '12',
        ]))

    # Optional archive presence gets logged but does not fail the bootstrap.
    optional = {name: {'path': str(path), 'exists': path.exists()} for name, path in OPTIONAL_SOURCES.items()}

    steps.append(run([
        sys.executable,
        'scripts/training/run_candidate_artifact_chain.py',
        '--candidate',
        args.candidate,
        '--base-model',
        args.base_model,
        '--mode',
        args.mode,
    ]))

    env_template = write_env_template(out_dir, args.candidate, args.base_model)

    ok = all(step['returncode'] == 0 for step in steps)
    summary = {
        'ok': ok,
        'created_at': now(),
        'candidate': args.candidate,
        'base_model_ref': args.base_model,
        'mode': args.mode,
        'root': str(ROOT),
        'env_template': str(env_template),
        'required_sources': {name: str(path) for name, path in DEFAULT_SOURCES.items()},
        'optional_sources': optional,
        'steps': steps,
        'next_action': (
            'Provide a real pretrained or merged model directory plus llama.cpp conversion tooling, then '
            'copy the generated env template to configs/production/real_gguf_build.env and run '
            'scripts/production/build_real_gguf_handoff.sh'
        ),
    }
    manifest = out_dir / 'bootstrap_manifest.json'
    manifest.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
