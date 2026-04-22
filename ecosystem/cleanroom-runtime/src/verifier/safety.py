from __future__ import annotations

from pathlib import Path


def path_within_workspace(root: str | Path, candidate: str | Path) -> bool:
    root_path = Path(root).resolve()
    candidate_path = Path(candidate).resolve()
    return str(candidate_path).startswith(str(root_path))
