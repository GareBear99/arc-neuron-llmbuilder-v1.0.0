from __future__ import annotations

import importlib.util
from pathlib import Path


def test_version_audit_passes_on_repo_state():
    script_path = Path(__file__).resolve().parents[1] / 'scripts' / 'version_audit.py'
    spec = importlib.util.spec_from_file_location('version_audit', script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
