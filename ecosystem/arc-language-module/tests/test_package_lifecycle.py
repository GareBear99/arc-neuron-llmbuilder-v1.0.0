from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.package_lifecycle import (
    build_translation_install_plan,
    record_translation_install_plan,
    list_translation_install_plans,
)


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_local_seed_install_plan_requires_no_install():
    result = build_translation_install_plan('lang:spa', 'lang:eng', provider_name='local_seed')
    assert result['ok'] is True
    assert result['readiness'] == 'ready'
    assert result['next_action'] == 'no_install_required'
    assert any('seed' in step.lower() for step in result['steps'])


def test_argos_install_plan_exposes_missing_dependency_or_pair():
    result = build_translation_install_plan('lang:spa', 'lang:eng', provider_name='argos_local')
    assert result['ok'] is True
    assert result['provider_name'] == 'argos_local'
    assert result['next_action'] in {'install_dependency', 'install_language_pair', 'ready_to_execute', 'map_runtime_codes'}
    if result['next_action'] == 'install_dependency':
        assert 'argostranslate' in result['missing']['dependencies']


def test_record_and_list_install_plan():
    saved = record_translation_install_plan('lang:spa', 'lang:eng', provider_name='local_seed', notes=['test plan'])
    assert saved['ok'] is True
    listing = list_translation_install_plans(provider_name='local_seed', source_language_id='lang:spa', target_language_id='lang:eng')
    assert listing['ok'] is True
    assert listing['results']
    latest = listing['results'][0]
    assert latest['provider_name'] == 'local_seed'
    assert latest['source_language_id'] == 'lang:spa'
    assert latest['target_language_id'] == 'lang:eng'
    assert latest['notes'] == ['test plan']
