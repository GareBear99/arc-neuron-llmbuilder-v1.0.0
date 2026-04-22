from __future__ import annotations

from fastapi import APIRouter

from arc_lang.api.http import raise_http_error_if, raise_http_error_unless_ok
from arc_lang.core.models import AcquisitionJobRequest, IngestionWorkspaceExportRequest, StagedAssetRequest, ValidationReportRequest
from arc_lang.services.acquisition_workspace import export_ingestion_workspace, list_acquisition_jobs, list_validation_reports, plan_acquisition_job, record_staged_asset, validate_staged_asset

router = APIRouter()


@router.post('/acquisition/jobs')
def acquisition_job_route(req: AcquisitionJobRequest) -> dict:
    return raise_http_error_unless_ok(plan_acquisition_job(req), status_code=404)


@router.get('/acquisition/jobs')
def acquisition_jobs_route(corpus_name: str | None = None) -> dict:
    return list_acquisition_jobs(corpus_name=corpus_name)


@router.post('/acquisition/assets')
def acquisition_asset_route(req: StagedAssetRequest) -> dict:
    return raise_http_error_unless_ok(record_staged_asset(req), status_code=404)


@router.post('/acquisition/validate')
def acquisition_validate_route(req: ValidationReportRequest) -> dict:
    result = validate_staged_asset(req)
    raise_http_error_if(not result.get('ok') and result.get('error') == 'file_not_found', status_code=404, detail=result)
    return result


@router.get('/acquisition/validation-reports')
def acquisition_validation_reports_route(limit: int = 50) -> dict:
    return list_validation_reports(limit=limit)


@router.post('/acquisition/export-workspace')
def acquisition_export_workspace_route(req: IngestionWorkspaceExportRequest) -> dict:
    return export_ingestion_workspace(req)
