
from pathlib import Path

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.provider_registry import register_provider, set_provider_health
from arc_lang.services.policy import get_policy_snapshot, set_operator_policy
from arc_lang.services.orchestration import route_runtime_translation
from arc_lang.services.provider_actions import execute_provider_action
from arc_lang.core.models import RuntimeTranslateRequest, BackendActionRequest
from arc_lang.services.evidence_export import export_evidence_bundle
from arc_lang.services.system_status import get_system_status


def setup_module(module):
    init_db()
    ingest_common_seed()
    register_provider('argos_bridge', 'translation', enabled=True, local_only=False)
    set_provider_health('argos_bridge', 'healthy')


def test_policy_defaults_present():
    snap = get_policy_snapshot()
    assert snap['ok']
    assert snap['policy_values']['runtime_default_dry_run'] == 'true'
    assert snap['policy_flags']['allow_external_providers'] is True


def test_external_provider_blocked_by_policy():
    set_operator_policy('allow_external_providers', 'false', notes='test external block')
    result = route_runtime_translation(RuntimeTranslateRequest(text='hola', target_language_id='lang:eng', source_language_id='lang:spa', preferred_translation_provider='argos_bridge', dry_run=False))
    assert result['ok'] is False
    assert result['error'] == 'external_provider_blocked_by_policy'


def test_mutation_action_blocked_by_policy():
    result = execute_provider_action(BackendActionRequest(provider_name='argos_local', source_language_id='lang:spa', target_language_id='lang:eng', action_name='install_dependency', dry_run=False, allow_mutation=True))
    assert result['ok'] is False
    assert result['error'] == 'provider_action_mutation_blocked_by_policy'


def test_evidence_export_and_status(tmp_path: Path):
    set_operator_policy('allow_external_providers', 'true', notes='test override')
    out = tmp_path / 'bundle.json'
    exported = export_evidence_bundle(str(out), language_ids=['lang:spa', 'lang:eng'])
    assert exported['ok']
    assert out.exists()
    status = get_system_status()
    assert status['ok']
    assert 'policy' in status
    assert status['receipts']['evidence_exports'] >= 1

def test_system_status_and_evidence_include_provider_counts(tmp_path: Path):
    out = tmp_path / 'bundle_counts.json'
    exported = export_evidence_bundle(str(out), language_ids=['lang:spa'])
    assert exported['ok']
    assert exported['summary']['provider_count'] >= 1

    status = get_system_status()
    assert status['provider_summary']['total_registered'] >= 1
    assert status['provider_summary']['enabled'] >= 1

