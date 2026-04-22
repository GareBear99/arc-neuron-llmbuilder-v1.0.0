from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / 'pyproject.toml'
README = ROOT / 'README.md'
PKG_INFO = ROOT / 'src' / 'arc_lucifer_cleanroom_runtime.egg-info' / 'PKG-INFO'
DIST = ROOT / 'dist'


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def _extract(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise SystemExit(f'Version audit failed: could not find {label}.')
    return match.group(1)


def main() -> int:
    pyproject_version = _extract(r'^version\s*=\s*"([^"]+)"', _read(PYPROJECT), 'pyproject version')
    readme_version = _extract(r'^## Current package state \(v([^\)]+)\)', _read(README), 'README package state')
    pkg_info_version = _extract(r'^Version:\s*([^\s]+)', _read(PKG_INFO), 'PKG-INFO version') if PKG_INFO.exists() else pyproject_version

    problems: list[str] = []
    versions = {
        'pyproject.toml': pyproject_version,
        'README.md': readme_version,
        'PKG-INFO': pkg_info_version,
    }
    if len(set(versions.values())) != 1:
        problems.append(f'metadata mismatch: {versions}')

    dist_versions: set[str] = set()
    if DIST.exists():
        for item in DIST.iterdir():
            match = re.search(r'-(\d+\.\d+\.\d+)', item.name)
            if match:
                dist_versions.add(match.group(1))
        if dist_versions and dist_versions != {pyproject_version}:
            problems.append(f'dist artifact versions do not match pyproject: {sorted(dist_versions)} vs {pyproject_version}')

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1

    print(pyproject_version)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
