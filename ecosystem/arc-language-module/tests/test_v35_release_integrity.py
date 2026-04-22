from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.api.app import app
from arc_lang.cli.parser import parse_args
from arc_lang.core.db import init_db
from arc_lang.services.release_integrity import get_release_snapshot
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.version import VERSION

client = TestClient(app)


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_release_snapshot_is_consistent():
    snap = get_release_snapshot()
    assert snap["ok"] is True
    assert snap["version"] == VERSION
    assert snap["pyproject_version"] == VERSION
    assert snap["checks"]["package_matches_pyproject"] is True
    assert snap["checks"]["api_app_uses_version_constant"] is True
    assert snap["checks"]["health_route_uses_version_constant"] is True


def test_release_snapshot_api_route():
    response = client.get('/release-snapshot')
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['version'] == VERSION
    assert body['graph_counts']['languages'] >= 35


def test_cli_parser_accepts_release_snapshot_command():
    args = parse_args(['release-snapshot'])
    assert args.cmd == 'release-snapshot'
