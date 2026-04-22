from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang import __version__
from arc_lang.api.app import app
from arc_lang.core.db import init_db
from arc_lang.services.release_integrity import get_release_snapshot
from arc_lang.services.seed_ingest import _load_seed_payloads, ingest_common_seed
from arc_lang.version import VERSION


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_version_is_single_sourced_across_public_surfaces():
    snapshot = get_release_snapshot()
    assert VERSION == __version__ == snapshot["version"]
    assert snapshot["checks"]["package_matches_pyproject"] is True
    assert app.version == VERSION


def test_seed_payload_loader_includes_all_required_sections():
    payloads = _load_seed_payloads(None, None, None)
    assert set(payloads) == {
        "languages",
        "phrases",
        "etymology",
        "pronunciation",
        "phonology",
        "transliteration",
        "variants",
        "concepts",
    }
    assert len(payloads["languages"].get("languages", [])) >= 35
    assert len(payloads["phrases"].get("phrases", [])) >= 10


def test_ingest_common_seed_returns_expected_core_counts():
    result = ingest_common_seed()
    assert result["ok"] is True
    assert result["languages"] >= 35
    assert result["phrase_translations"] >= 300
    assert result["semantic_concepts"] >= 10
