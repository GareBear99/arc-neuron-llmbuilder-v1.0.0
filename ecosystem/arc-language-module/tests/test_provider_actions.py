from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.provider_actions import build_provider_action_catalog, execute_provider_action, list_provider_action_receipts
from arc_lang.core.models import BackendActionRequest


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_provider_action_catalog_for_argos_local():
    result = build_provider_action_catalog('lang:spa', 'lang:eng', 'argos_local')
    assert result['ok'] is True
    names = {a['action_name'] for a in result['actions']}
    assert 'install_dependency' in names
    assert 'install_language_pair' in names


def test_provider_action_execute_dry_run_receipt():
    result = execute_provider_action(BackendActionRequest(
        provider_name='argos_local',
        source_language_id='lang:spa',
        target_language_id='lang:eng',
        action_name='install_dependency',
        dry_run=True,
        allow_mutation=False,
    ))
    assert result['ok'] is True
    assert result['receipt']['status'] == 'dry_run'
    receipts = list_provider_action_receipts(provider_name='argos_local', action_name='install_dependency', limit=5)
    assert receipts['ok'] is True
    assert any(r['action_receipt_id'] == result['receipt']['action_receipt_id'] for r in receipts['results'])


def test_provider_action_mutation_blocked_without_flag():
    result = execute_provider_action(BackendActionRequest(
        provider_name='argos_local',
        source_language_id='lang:spa',
        target_language_id='lang:eng',
        action_name='install_dependency',
        dry_run=False,
        allow_mutation=False,
    ))
    assert result['ok'] is False
    assert result['error'] == 'provider_action_mutation_blocked'
    assert result['receipt']['status'] == 'blocked'
