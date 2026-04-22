from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_command_adapter_supports_combined_prompt_file(tmp_path: Path):
    script = tmp_path / "echo_prompt.py"
    script.write_text(
        "import sys, pathlib\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "print(p.read_text(encoding='utf-8').splitlines()[-1])\n",
        encoding="utf-8",
    )
    out = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "scripts" / "execution" / "run_direct_candidate.py"),
            "--adapter",
            "command",
            "--command-template",
            f"{sys.executable} {script} {{combined_prompt_file}}",
            "--prompt",
            "Quoted prompt with spaces and symbols: [x] {y} 'z' \"q\"",
        ],
        cwd=ROOT,
        text=True,
    )
    payload = json.loads(out)
    assert payload["ok"] is True
    assert "Quoted prompt with spaces" in payload["text"]


def test_doctor_runtime_exemplar_path():
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "scripts" / "training" / "train_exemplar_candidate.py"),
            "--candidate",
            "doctor_test",
        ],
        cwd=ROOT,
    )
    out = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "scripts" / "runtime" / "doctor_direct_runtime.py"),
            "--adapter",
            "exemplar",
            "--artifact",
            str(ROOT / "exports" / "candidates" / "doctor_test" / "exemplar_train" / "artifact_manifest.json"),
        ],
        cwd=ROOT,
        text=True,
    )
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["user_end_summary"]["server_required"] is False
