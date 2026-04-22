from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_command_adapter_first_output_timeout() -> None:
    command_template = f'{sys.executable} -c "import time; time.sleep(1.0)"'
    proc = subprocess.run(
        [
            sys.executable,
            'scripts/execution/run_direct_candidate.py',
            '--adapter', 'command',
            '--command-template', command_template,
            '--prompt', 'hi',
            '--first-output-timeout-seconds', '0.2',
            '--timeout-seconds', '2.0',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload['ok'] is False
    assert payload['finish_reason'] == 'stalled_tokenization'


def test_compile_llamafile_from_binary_script(tmp_path: Path) -> None:
    runtime_binary = tmp_path / 'runtime.bin'
    gguf = tmp_path / 'model.gguf'
    output = tmp_path / 'model.llamafile'
    runtime_binary.write_bytes(b'BIN')
    gguf.write_bytes(b'GGUF')

    proc = subprocess.run(
        [
            sys.executable,
            'scripts/runtime/compile_llamafile_from_binary.py',
            '--runtime-binary', str(runtime_binary),
            '--gguf', str(gguf),
            '--output', str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload['ok'] is True
    assert output.read_bytes() == b'BINGGUF'
