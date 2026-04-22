
from pathlib import Path
from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.manifests import seed_manifests
from arc_lang.services.acquisition_workspace import plan_acquisition_job, record_staged_asset, validate_staged_asset, export_ingestion_workspace
from arc_lang.core.models import AcquisitionJobRequest, StagedAssetRequest, ValidationReportRequest, IngestionWorkspaceExportRequest


def test_plan_acquisition_job_and_record_asset(tmp_path: Path):
    init_db(); ingest_common_seed(); seed_manifests()
    planned = plan_acquisition_job(AcquisitionJobRequest(corpus_name='Glottolog', output_dir=str(tmp_path / 'stage')))
    assert planned['ok'] is True
    sample = tmp_path / 'sample.csv'
    sample.write_text('id,name\n1,test\n', encoding='utf-8')
    asset = record_staged_asset(StagedAssetRequest(job_id=planned['job_id'], file_path=str(sample), asset_kind='csv'))
    assert asset['ok'] is True
    assert asset['file_size_bytes'] > 0
    assert len(asset['sha256']) == 64


def test_validate_staged_asset_csv_and_export_workspace(tmp_path: Path):
    init_db(); ingest_common_seed(); seed_manifests()
    sample = tmp_path / 'sample.csv'
    sample.write_text('id,name\n1,test\n', encoding='utf-8')
    report = validate_staged_asset(ValidationReportRequest(file_path=str(sample), expected_kind='csv'))
    assert report['ok'] is True
    assert report['detected_kind'] == 'csv'
    out = tmp_path / 'workspace.json'
    export = export_ingestion_workspace(IngestionWorkspaceExportRequest(output_path=str(out)))
    assert export['ok'] is True
    assert out.exists()
    assert export['summary']['validation_reports'] >= 1


def test_validate_kind_mismatch_fails(tmp_path: Path):
    init_db(); ingest_common_seed(); seed_manifests()
    sample = tmp_path / 'sample.json'
    sample.write_text('{"ok": true}', encoding='utf-8')
    report = validate_staged_asset(ValidationReportRequest(file_path=str(sample), expected_kind='csv'))
    assert report['ok'] is False
    assert report['status'] == 'failed'
