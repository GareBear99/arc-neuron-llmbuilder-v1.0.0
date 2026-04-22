"""
test_v25_hardening.py

Covers every surface added or changed across sessions 2-3:
  - Importer dry_run mode
  - Importer inserted/updated dedup counters
  - Importer conflict detection
  - Expanded get_graph_stats (all 39 tables)
  - Coverage report new fields (phonology, lineage_edges, alias_by_type, gap flags)
  - Coverage report output_path
  - CLI: new commands smoke-test via function calls
  - Phonology: upsert + list + hint
  - Implementation matrix: build + list
  - Acquisition CLI: plan, record-asset, validate, list, export-workspace
  - PhonologyProfileUpsertRequest model validation
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db, connect
from arc_lang.core.models import (
    PhonologyProfileUpsertRequest,
    CoverageReportRequest,
    AcquisitionJobRequest,
    StagedAssetRequest,
    ValidationReportRequest,
    IngestionWorkspaceExportRequest,
)
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.importers import import_glottolog_csv, import_iso639_csv, import_cldr_json
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.coverage import build_coverage_report, list_coverage_reports
from arc_lang.services.phonology import upsert_phonology_profile, list_phonology_profiles, phonology_hint
from arc_lang.services.implementation_matrix import build_implementation_matrix, list_implementation_matrix_reports
from arc_lang.services.acquisition_workspace import (
    plan_acquisition_job, record_staged_asset, validate_staged_asset,
    list_acquisition_jobs, list_validation_reports, export_ingestion_workspace,
)
from arc_lang.services.manual_lineage import add_custom_lineage
from arc_lang.core.models import ManualLineageRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


# ─── Importer: dry_run mode ────────────────────────────────────────────────

def test_glottolog_dry_run_produces_no_import_run():
    path = ROOT / "examples" / "glottolog_sample.csv"
    result = import_glottolog_csv(path, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["import_id"] == ""
    assert result["records_seen"] >= 3     # example file has 6 rows now
    assert result["records_inserted"] == 0  # dry run: no mutations
    with connect() as conn:
        count_before = conn.execute(
            "SELECT COUNT(*) AS c FROM import_runs WHERE source_name='glottolog'"
        ).fetchone()["c"]
    import_glottolog_csv(path, dry_run=True)  # second dry_run
    with connect() as conn:
        count_after = conn.execute(
            "SELECT COUNT(*) AS c FROM import_runs WHERE source_name='glottolog'"
        ).fetchone()["c"]
    assert count_after == count_before  # dry_run must not create import_run rows


def test_iso639_dry_run_produces_no_import_run():
    path = ROOT / "examples" / "iso6393_sample.csv"
    result = import_iso639_csv(path, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["import_id"] == ""
    assert result["records_seen"] >= 1


def test_cldr_dry_run_produces_no_import_run():
    path = ROOT / "examples" / "cldr_sample.json"
    result = import_cldr_json(path, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["import_id"] == ""
    assert result["records_seen"] >= 1


def test_live_import_populates_inserted_updated_counters():
    path = ROOT / "examples" / "glottolog_sample.csv"
    # First live import — may insert or update depending on seed state
    result = import_glottolog_csv(path, dry_run=False)
    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["import_id"] != ""
    assert result["records_seen"] >= 3   # example file has 6 rows
    assert result["records_upserted"] == result["records_inserted"] + result["records_updated"]
    # Second live import of same file — all rows should now be updates
    result2 = import_glottolog_csv(path, dry_run=False)
    assert result2["records_inserted"] == 0
    assert result2["records_updated"] == result2["records_seen"]


def test_conflict_detection_fires_on_custom_lineage_collision():
    """Add a custom lineage assertion for lang:nav, then import glottolog — conflicts should be detected."""
    add_custom_lineage(ManualLineageRequest(
        src_id="lang:nav",
        dst_id="family:na_dene",
        relation="custom_member_of_family",
        confidence=0.7,
        notes="test conflict detection",
    ))
    path = ROOT / "examples" / "glottolog_sample.csv"
    result = import_glottolog_csv(path, dry_run=True)
    assert result["conflict_count"] >= 1
    assert any(c["language_id"] == "lang:nav" for c in result["conflicts"])


# ─── Stats: all 39 tables ────────────────────────────────────────────────

def test_graph_stats_covers_all_required_tables():
    stats = get_graph_stats()
    counts = stats["counts"]
    required = [
        "languages", "scripts", "language_scripts", "lineage_nodes", "lineage_edges",
        "phrase_translations", "lexemes", "etymology_edges",
        "language_aliases", "relationship_assertions",
        "language_variants", "semantic_concepts", "concept_links",
        "pronunciation_profiles", "phonology_profiles", "transliteration_profiles",
        "language_submissions", "custom_lineage_assertions", "review_decisions", "language_capabilities",
        "provenance_records", "import_runs", "batch_io_runs", "source_weights",
        "providers", "provider_health", "job_receipts", "provider_action_receipts",
        "translation_install_plans",
        "backend_manifests", "corpus_manifests", "implementation_matrix_reports",
        "acquisition_jobs", "staged_assets", "validation_reports",
        "evidence_exports", "conflict_review_exports", "coverage_reports",
        "ingestion_workspace_exports",
    ]
    for key in required:
        assert key in counts, f"Missing key in graph stats: {key}"
    assert len(counts) >= 39


def test_graph_stats_phonology_nonzero_after_seed():
    stats = get_graph_stats()
    assert stats["counts"]["phonology_profiles"] >= 12
    assert stats["counts"]["transliteration_profiles"] >= 11


# ─── Coverage report: new fields ────────────────────────────────────────

def test_coverage_report_contains_new_fields():
    req = CoverageReportRequest(language_ids=["lang:eng", "lang:jpn", "lang:chr"])
    result = build_coverage_report(req)
    assert result["ok"] is True
    for item in result["items"]:
        assert "phonology_profiles" in item
        assert "lineage_edges" in item
        assert "custom_lineage_assertions" in item
        assert "aliases_by_type" in item
        assert "missing_phonology" in item
        assert "missing_transliteration" in item
        assert "missing_pronunciation" in item
        assert "missing_script" in item
        assert "family" in item
        assert "capabilities" in item


def test_coverage_report_summary_has_gap_fields():
    req = CoverageReportRequest()
    result = build_coverage_report(req)
    summary = result["summary"]
    assert "with_phonology_profiles" in summary
    assert "missing_phonology" in summary
    assert "missing_transliteration" in summary
    assert "with_lineage_edges" in summary


def test_coverage_report_eng_has_phonology():
    req = CoverageReportRequest(language_ids=["lang:eng"])
    result = build_coverage_report(req)
    eng = result["items"][0]
    assert eng["phonology_profiles"] >= 1
    assert eng["missing_phonology"] is False


def test_coverage_report_output_path(tmp_path: Path):
    out = tmp_path / "coverage.json"
    req = CoverageReportRequest(output_path=str(out), language_ids=["lang:spa", "lang:fra"])
    result = build_coverage_report(req)
    assert result["ok"] is True
    assert out.exists()
    assert "report_id" in result
    loaded = json.loads(out.read_text())
    assert loaded["ok"] is True
    assert len(loaded["items"]) == 2
    # Persisted to DB
    reports = list_coverage_reports()
    assert reports["count"] >= 1


# ─── Phonology ────────────────────────────────────────────────────────────

def test_upsert_phonology_profile_roundtrip():
    result = upsert_phonology_profile(
        "lang:eng", "narrow_ipa",
        broad_ipa="ɪŋɡlɪʃ",
        stress_policy="lexical_stress",
        syllable_template="(C)(C)(C)V(C)(C)(C)",
        examples={"ship": "ʃɪp", "sheep": "ʃiːp"},
        notes="Narrow test profile",
    )
    assert result["ok"] is True
    profiles = list_phonology_profiles(language_id="lang:eng")
    assert profiles["ok"] is True
    notation_systems = [p["notation_system"] for p in profiles["results"]]
    assert "narrow_ipa" in notation_systems
    assert "broad_ipa" in notation_systems  # from seed


def test_list_phonology_profiles_all():
    profiles = list_phonology_profiles()
    assert profiles["ok"] is True
    assert len(profiles["results"]) >= 12


def test_phonology_hint_returns_data():
    result = phonology_hint("hello", "lang:eng")
    assert result["ok"] is True
    assert result["language_id"] == "lang:eng"
    assert "notation_system" in result
    assert "stress_policy" in result


def test_phonology_hint_missing_language_returns_error():
    result = phonology_hint("nope", "lang:zzz_nonexistent")
    assert result["ok"] is False
    assert result["error"] == "phonology_profile_not_found"


def test_phonology_profile_upsert_request_model():
    req = PhonologyProfileUpsertRequest(
        language_id="lang:deu",
        notation_system="broad_ipa",
        broad_ipa="dɔʏtʃ",
        stress_policy="root_initial",
        examples={"danke": "ˈdaŋkə"},
        notes="test",
    )
    assert req.language_id == "lang:deu"
    assert req.examples["danke"] == "ˈdaŋkə"


# ─── Implementation matrix ────────────────────────────────────────────────

def test_build_implementation_matrix_returns_honest_summary():
    result = build_implementation_matrix()
    assert result["ok"] is True
    assert "report_id" in result
    summary = result["summary"]
    assert "implemented_in_package" in summary
    assert "external_data_required" in summary
    assert "external_runtime_required" in summary
    impl = summary["implemented_in_package"]
    assert impl["language_graph"] is True
    assert impl["runtime_routing"] is True


def test_build_implementation_matrix_output_path(tmp_path: Path):
    out = tmp_path / "matrix.json"
    result = build_implementation_matrix(output_path=str(out))
    assert result["ok"] is True
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded["ok"] is True


def test_list_implementation_matrix_reports():
    build_implementation_matrix()  # ensure at least one
    result = list_implementation_matrix_reports()
    assert result["ok"] is True
    assert len(result["results"]) >= 1
    first = result["results"][0]
    assert "summary" in first
    assert "report_id" in first


# ─── Acquisition workspace (service layer) ───────────────────────────────

def test_plan_acquisition_job_creates_record(tmp_path: Path):
    """plan_acquisition_job requires an existing corpus_manifest entry.
    Seed manifests are loaded during ingest_common_seed via seed_manifests().
    Use a corpus name that is present in the seeded manifests."""
    from arc_lang.services.manifests import list_corpus_manifests
    manifests = list_corpus_manifests()
    assert manifests["results"], "No corpus manifests seeded — seed_manifests() must run first"
    corpus_name = manifests["results"][0]["corpus_name"]
    result = plan_acquisition_job(AcquisitionJobRequest(
        corpus_name=corpus_name,
        stage_name="staging",
        output_dir=str(tmp_path / "stage"),
        notes="test acquisition job",
    ))
    assert result["ok"] is True, f"plan_acquisition_job failed: {result}"
    assert "job_id" in result
    assert result["corpus_name"] == corpus_name


def test_record_staged_asset_computes_hash(tmp_path: Path):
    from arc_lang.services.manifests import list_corpus_manifests
    manifests = list_corpus_manifests()
    corpus_name = manifests["results"][0]["corpus_name"]
    job = plan_acquisition_job(AcquisitionJobRequest(
        corpus_name=corpus_name,
        stage_name="staging",
        output_dir=str(tmp_path / "stage2"),
    ))
    assert job["ok"] is True
    f = tmp_path / "sample.csv"
    f.write_text("id,name\n1,hello\n", encoding="utf-8")
    asset = record_staged_asset(StagedAssetRequest(
        job_id=job["job_id"],
        file_path=str(f),
        asset_kind="csv",
    ))
    assert asset["ok"] is True
    assert len(asset["sha256"]) == 64
    assert asset["file_size_bytes"] > 0


def test_validate_staged_asset_csv_pass(tmp_path: Path):
    f = tmp_path / "data.csv"
    f.write_text("col1,col2\na,b\n", encoding="utf-8")
    report = validate_staged_asset(ValidationReportRequest(file_path=str(f), expected_kind="csv"))
    assert report["ok"] is True
    assert report["detected_kind"] == "csv"
    assert report["status"] == "passed"


def test_validate_staged_asset_kind_mismatch_fails(tmp_path: Path):
    f = tmp_path / "data.json"
    f.write_text('{"key": "val"}', encoding="utf-8")
    report = validate_staged_asset(ValidationReportRequest(file_path=str(f), expected_kind="csv"))
    assert report["ok"] is False
    assert report["status"] == "failed"


def test_list_acquisition_jobs_filters_by_corpus():
    plan_acquisition_job(AcquisitionJobRequest(corpus_name="FilterMe", stage_name="staging"))
    result = list_acquisition_jobs(corpus_name="FilterMe")
    assert result["ok"] is True
    assert all(j["corpus_name"] == "FilterMe" for j in result["items"])


def test_list_validation_reports_returns_results():
    result = list_validation_reports()
    assert result["ok"] is True
    assert isinstance(result["items"], list)


def test_export_ingestion_workspace(tmp_path: Path):
    out = tmp_path / "workspace.json"
    result = export_ingestion_workspace(IngestionWorkspaceExportRequest(output_path=str(out)))
    assert result["ok"] is True
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert "summary" in loaded
    summary = loaded["summary"]
    # Keys must match what the service actually produces (batch_runs, not batch_io_runs)
    for key in ("corpus_manifests", "import_runs", "batch_runs", "validation_reports", "acquisition_jobs"):
        assert key in summary, f"Missing key in workspace export summary: {key}"


# ─── Seed data integrity ─────────────────────────────────────────────────

def test_phonology_seed_covers_all_expected_languages():
    expected = {
        "lang:eng", "lang:spa", "lang:fra", "lang:deu", "lang:rus",
        "lang:hin", "lang:jpn", "lang:kor", "lang:cmn", "lang:arb",  # cmn not zho
        "lang:tur", "lang:tha",
    }
    profiles = list_phonology_profiles()
    seeded_ids = {p["language_id"] for p in profiles["results"]}
    missing = expected - seeded_ids
    assert not missing, f"Missing phonology profiles for: {missing}"


def test_transliteration_seed_covers_expected_scripts():
    with connect() as conn:
        rows = conn.execute(
            "SELECT language_id, source_script, scheme_name FROM transliteration_profiles ORDER BY language_id"
        ).fetchall()
    profiles = [(r["language_id"], r["source_script"]) for r in rows]
    assert ("lang:rus", "Cyrl") in profiles
    assert ("lang:jpn", "Hira") in profiles
    assert ("lang:jpn", "Kana") in profiles
    assert ("lang:kor", "Hang") in profiles
    assert ("lang:cmn", "Hans") in profiles   # cmn not zho
    assert ("lang:ell", "Grek") in profiles
    assert ("lang:tha", "Thai") in profiles
