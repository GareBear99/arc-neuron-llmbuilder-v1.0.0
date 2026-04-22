from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMMANDS = {
    "validate": [sys.executable, str(ROOT / "scripts" / "validate_repo.py")],
    "count-data": [sys.executable, str(ROOT / "scripts" / "build_dataset.py")],
    "count-benchmarks": [sys.executable, str(ROOT / "scripts" / "run_benchmarks.py")],
    "backend-check": [sys.executable, str(ROOT / "scripts" / "execution" / "check_local_backend.py")],
    "candidate-gate": [sys.executable, str(ROOT / "scripts" / "execution" / "run_full_candidate_gate.py")],
    "train-functioning-model": [sys.executable, str(ROOT / "scripts" / "training" / "train_exemplar_candidate.py"), "--candidate", "darpa_functional"],
    "run-functioning-model": [sys.executable, str(ROOT / "scripts" / "execution" / "run_functioning_candidate.py"), "--candidate", "darpa_functional"],
    "doctor-runtime": [sys.executable, str(ROOT / "scripts" / "runtime" / "doctor_direct_runtime.py"), "--adapter", "exemplar", "--artifact", str(ROOT / "exports" / "candidates" / "darpa_functional" / "exemplar_train" / "artifact_manifest.json")],
    "compile-llamafile-help": [sys.executable, str(ROOT / "scripts" / "runtime" / "compile_llamafile_from_binary.py"), "--help"],
    "user-prompt-help": ["bash", str(ROOT / "scripts" / "operator" / "run_local_prompt.sh")],
    "benchmark-local-help": ["bash", str(ROOT / "scripts" / "operator" / "benchmark_local_model.sh")],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cognition lab control entrypoint")
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args()
    raise SystemExit(subprocess.call(COMMANDS[args.command], cwd=ROOT))


if __name__ == "__main__":
    main()
