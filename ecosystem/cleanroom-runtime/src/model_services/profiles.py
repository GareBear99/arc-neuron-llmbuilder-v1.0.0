from __future__ import annotations

"""Persistent profile registry for local and future model backends.

Profiles keep the runtime open-ended: any GGUF-capable or external backend can be
registered as metadata first, then wired to a concrete adapter later.
"""

import json
from pathlib import Path
from typing import Any


class ModelProfileStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'model_profiles.json'

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {'active_profile': None, 'profiles': {}}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('model_profiles.json must contain an object')
        data.setdefault('active_profile', None)
        data.setdefault('profiles', {})
        return data

    def _save(self, payload: dict[str, Any]) -> Path:
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return self.path

    def list_profiles(self) -> dict[str, Any]:
        payload = self._load()
        return {
            'status': 'ok',
            'active_profile': payload.get('active_profile'),
            'profiles': [
                {'name': name, **profile}
                for name, profile in sorted(payload.get('profiles', {}).items())
            ],
            'profile_path': str(self.path),
        }

    def register_profile(self, name: str, profile: dict[str, Any], activate: bool = False) -> dict[str, Any]:
        payload = self._load()
        payload['profiles'][name] = profile
        if activate or payload.get('active_profile') is None:
            payload['active_profile'] = name
        self._save(payload)
        return {
            'status': 'ok',
            'name': name,
            'profile': {'name': name, **profile},
            'active_profile': payload.get('active_profile'),
            'profile_path': str(self.path),
        }

    def show_profile(self, name: str) -> dict[str, Any]:
        payload = self._load()
        profile = payload.get('profiles', {}).get(name)
        if profile is None:
            return {'status': 'not_found', 'reason': f'Unknown profile: {name}', 'profile_path': str(self.path)}
        return {'status': 'ok', 'active_profile': payload.get('active_profile'), 'profile': {'name': name, **profile}, 'profile_path': str(self.path)}

    def activate_profile(self, name: str) -> dict[str, Any]:
        payload = self._load()
        if name not in payload.get('profiles', {}):
            return {'status': 'not_found', 'reason': f'Unknown profile: {name}', 'profile_path': str(self.path)}
        payload['active_profile'] = name
        self._save(payload)
        return {'status': 'ok', 'active_profile': name, 'profile_path': str(self.path)}

    def active_profile(self) -> dict[str, Any] | None:
        payload = self._load()
        name = payload.get('active_profile')
        if not name:
            return None
        profile = payload.get('profiles', {}).get(name)
        if profile is None:
            return None
        return {'name': name, **profile}

    def compare_profiles(self, names: list[str]) -> dict[str, Any]:
        payload = self._load()
        rows = []
        for name in names:
            profile = payload.get('profiles', {}).get(name)
            if profile is None:
                rows.append({'name': name, 'status': 'missing'})
                continue
            rows.append({
                'name': name,
                'status': 'ok',
                'backend_type': profile.get('backend_type'),
                'binary_path': profile.get('binary_path'),
                'model_path': profile.get('model_path'),
                'endpoint': profile.get('endpoint'),
                'notes': profile.get('notes', ''),
                'intended_use': profile.get('intended_use', ''),
                'training_ready': bool(profile.get('training_ready', False)),
            })
        return {'status': 'ok', 'active_profile': payload.get('active_profile'), 'profiles': rows, 'profile_path': str(self.path)}
