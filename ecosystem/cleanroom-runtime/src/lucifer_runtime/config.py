from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_ENV = 'ARC_LUCIFER_CONFIG'
DEFAULT_CONFIG_NAME = 'config.json'
DEFAULT_RUNTIME_DIR = '.arc_lucifer'


def default_runtime_dir(workspace: str | Path) -> Path:
    workspace_path = Path(workspace).expanduser().resolve()
    return workspace_path / DEFAULT_RUNTIME_DIR


def default_config_path(workspace: str | Path) -> Path:
    return default_runtime_dir(workspace) / DEFAULT_CONFIG_NAME


def load_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        return {}
    data = json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Config file must contain a JSON object.')
    return data


def save_config(path: str | Path, data: dict[str, Any]) -> Path:
    config_path = Path(path).expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return config_path


def merge_settings(*sources: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merge_settings(merged[key], value)
            elif value is not None:
                merged[key] = value
    return merged
