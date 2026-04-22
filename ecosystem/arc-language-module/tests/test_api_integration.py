"""
test_api_integration.py

FastAPI integration tests via TestClient — covers all 28 previously-untested
route handlers. Each test hits the actual HTTP layer to verify routing, request
parsing, and response shape.

Tests are deliberately lightweight (happy-path + basic error-path) — full
business logic is verified in the service-level unit tests.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest
from fastapi.testclient import TestClient

from arc_lang.api.app import app
from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed

client = TestClient(app)


def setup_module(module):
    init_db()
    ingest_common_seed()


# ── Health / meta ────────────────────────────────────────────────────────────

def test_health_route():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["version"] == "0.27.0"


def test_stats_route():
    r = client.get("/stats")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["counts"]["languages"] >= 35


# ── Governance: capabilities ──────────────────────────────────────────────

def test_capability_set_route():
    r = client.post("/capabilities/set", json={
        "language_id": "lang:eng",
        "capability_name": "translation",
        "maturity": "production",
        "confidence": 0.95,
        "provider": "local_seed",
        "notes": "API test",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_capability_list_route():
    r = client.get("/capabilities")
    assert r.status_code == 200
    assert isinstance(r.json().get("items") or r.json().get("results", []), list)


def test_capability_list_route_filtered():
    r = client.get("/capabilities", params={"language_id": "lang:eng"})
    assert r.status_code == 200


# ── Governance: reviews ───────────────────────────────────────────────────

def test_review_list_route():
    r = client.get("/governance/reviews")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_review_list_route_filtered():
    r = client.get("/governance/reviews", params={"target_type": "language_submission"})
    assert r.status_code == 200


# ── Runtime: translate + speak ────────────────────────────────────────────

def test_runtime_translate_route_dry_run():
    r = client.post("/runtime/translate", json={
        "text": "hello",
        "target_language_id": "lang:spa",
        "source_language_id": "lang:eng",
        "dry_run": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body


def test_runtime_speak_route_dry_run():
    """Speech is unavailable by default (maturity=none). Route returns 200 with ok=false
    or 422 with explicit capability error — both are valid honest responses."""
    r = client.post("/runtime/speak", json={
        "text": "hello",
        "language_id": "lang:eng",
        "dry_run": True,
    })
    # 422 = honest speech_capability_unavailable; 200 = ok response both acceptable
    assert r.status_code in (200, 422)
    body = r.json()
    if r.status_code == 422:
        # Must include explicit error reason
        detail = body.get("detail", body)
        assert "speech" in str(detail).lower() or "capability" in str(detail).lower()


def test_runtime_speak_route_disabled_provider():
    """Calling with provider=disabled always succeeds (disabled sink returns ok=False explicitly)."""
    r = client.post("/runtime/speak", json={
        "text": "hello",
        "language_id": "lang:eng",
        "provider": "disabled",
        "dry_run": True,
    })
    # The disabled provider is registered; route may or may not raise based on capability gate
    assert r.status_code in (200, 422)


# ── Providers ──────────────────────────────────────────────────────────────

def test_provider_register_route():
    r = client.post("/providers/register", json={
        "provider_name": "test_provider_api",
        "provider_type": "translation",
        "enabled": True,
        "local_only": True,
        "notes": "API integration test provider",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Install plans + provider actions ─────────────────────────────────────

def test_translation_install_plan_record_route():
    r = client.post("/runtime/install-plan/translation/record", json={
        "source_language_id": "lang:eng",
        "target_language_id": "lang:spa",
        "provider_name": "argos_local",
        "notes": [],
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_provider_actions_execute_route_dry_run():
    r = client.post("/runtime/provider-actions/execute", json={
        "provider_name": "argos_local",
        "source_language_id": "lang:eng",
        "target_language_id": "lang:fra",
        "dry_run": True,
        "allow_mutation": False,
        "notes": [],
    })
    assert r.status_code == 200


# ── Policy ────────────────────────────────────────────────────────────────

def test_policy_set_route():
    r = client.post("/policy/set", json={
        "policy_key": "runtime_default_dry_run",
        "policy_value": "true",
        "notes": "API integration test — restoring default",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Transliteration profiles ──────────────────────────────────────────────

def test_transliteration_profile_upsert_route():
    r = client.post("/transliteration/profiles/upsert", json={
        "language_id": "lang:rus",
        "source_script": "Cyrl",
        "target_script": "Latn",
        "scheme_name": "bgn_pcgn_updated",
        "coverage": "seeded",
        "example_in": "Россия",
        "example_out": "Rossiya",
        "notes": "Updated via API test",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Pronunciation ──────────────────────────────────────────────────────────

def test_pronounce_route():
    r = client.post("/pronounce", json={
        "text": "hello",
        "language_id": "lang:eng",
        "allow_detect": False,
        "target_script": "Latn",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Aliases ────────────────────────────────────────────────────────────────

def test_alias_list_route():
    r = client.get("/languages/aliases")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_alias_list_route_filtered():
    r = client.get("/languages/aliases", params={"language_id": "lang:eng"})
    assert r.status_code == 200


# ── Relationships ──────────────────────────────────────────────────────────

def test_relationship_list_route():
    r = client.get("/relationships")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_relationship_list_route_filtered():
    r = client.get("/relationships", params={"relation": "cognate"})
    assert r.status_code == 200


# ── Source weights ────────────────────────────────────────────────────────

def test_source_weight_set_route():
    r = client.post("/sources/weights/set", json={
        "source_name": "glottolog",
        "authority_weight": 1.0,
        "notes": "Restored via API test",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_source_weight_list_route():
    r = client.get("/sources/weights")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert len(r.json()["items"]) >= 7


# ── Semantic concepts ──────────────────────────────────────────────────────

def test_concepts_upsert_route():
    r = client.post("/concepts/upsert", json={
        "canonical_label": "rain / precipitation",
        "domain": "basic_vocabulary",
        "description": "Water falling from clouds.",
        "confidence": 0.90,
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["concept_id"]


def test_concepts_link_route():
    # Create concept first
    c = client.post("/concepts/upsert", json={
        "canonical_label": "test concept for link",
        "domain": "general",
        "confidence": 0.80,
    })
    concept_id = c.json()["concept_id"]

    r = client.post("/concepts/link", json={
        "concept_id": concept_id,
        "target_type": "language",
        "target_id": "lang:eng",
        "relation": "expresses",
        "confidence": 0.75,
        "notes": "API integration test link",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_concepts_list_route():
    r = client.get("/concepts")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert len(r.json()["items"]) >= 30


def test_concepts_bundle_route():
    r = client.get("/concepts/concept_greeting_hello")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["concept"]["concept_id"] == "concept_greeting_hello"


# ── Language variants ──────────────────────────────────────────────────────

def test_variants_upsert_route():
    r = client.post("/languages/variants/upsert", json={
        "language_id": "lang:ell",
        "variant_name": "Ancient Greek",
        "variant_type": "historical_stage",
        "mutual_intelligibility": 0.05,
        "notes": "Classical Attic/Koine — requires dedicated study from Modern Greek.",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_variants_list_route():
    r = client.get("/languages/variants")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["count"] >= 37


def test_variants_list_route_filtered():
    r = client.get("/languages/variants", params={"variant_type": "dialect"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(item["variant_type"] == "dialect" for item in items)


# ── Conflict review exports ────────────────────────────────────────────────

def test_conflicts_exports_list_route():
    r = client.get("/conflicts/exports")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_conflicts_export_route(tmp_path):
    out = str(tmp_path / "conflicts.json")
    r = client.post("/conflicts/export", json={
        "output_path": out,
        "language_ids": ["lang:eng", "lang:spa"],
        "include_unreviewed_only": False,
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Phonology upsert via API ───────────────────────────────────────────────

def test_phonology_upsert_route():
    r = client.post("/phonology/profiles/upsert", json={
        "language_id": "lang:ell",
        "notation_system": "narrow_ipa",
        "broad_ipa": "elinika",
        "stress_policy": "lexical_stress_marked",
        "syllable_template": "(C)(C)V(C)",
        "examples": {"γεια": "ja", "ναι": "ne"},
        "notes": "Narrow IPA test profile added via API.",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Acquisition routes ─────────────────────────────────────────────────────

def test_acquisition_validate_route(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text("col1,col2\na,b\n")
    r = client.post("/acquisition/validate", json={
        "file_path": str(f),
        "expected_kind": "csv",
        "notes": "API integration test",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_acquisition_validation_reports_route():
    r = client.get("/acquisition/validation-reports")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_acquisition_export_workspace_route(tmp_path):
    out = str(tmp_path / "workspace.json")
    r = client.post("/acquisition/export-workspace", json={
        "output_path": out,
        "include_corpus_manifests": True,
        "include_import_runs": True,
        "include_batch_runs": True,
        "include_validation_reports": True,
        "include_jobs": True,
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_acquisition_asset_route(tmp_path):
    # Need a job first — use seeded corpus manifest
    from arc_lang.services.manifests import list_corpus_manifests
    from arc_lang.services.acquisition_workspace import plan_acquisition_job
    from arc_lang.core.models import AcquisitionJobRequest
    manifests = list_corpus_manifests()
    corpus = manifests["results"][0]["corpus_name"]
    job = plan_acquisition_job(AcquisitionJobRequest(
        corpus_name=corpus, stage_name="staging",
        output_dir=str(tmp_path / "stage")
    ))
    f = tmp_path / "asset.csv"
    f.write_text("id,name\n1,test\n")
    r = client.post("/acquisition/assets", json={
        "job_id": job["job_id"],
        "file_path": str(f),
        "asset_kind": "csv",
        "notes": "API integration test asset",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
