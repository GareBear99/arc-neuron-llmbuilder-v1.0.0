from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.transliteration import transliterate, list_transliteration_profiles, upsert_transliteration_profile, transliterate_request
from arc_lang.core.models import TransliterationRequest
from arc_lang.services.governance import get_language_readiness
from arc_lang.services.system_status import get_system_status


def test_seeded_transliteration_profiles_present():
    init_db()
    ingest_common_seed()
    out = list_transliteration_profiles(language_id='lang:rus')
    assert out['ok'] is True
    assert any(r['source_script'] == 'Cyrl' for r in out['results'])


def test_transliteration_returns_profile_context():
    init_db()
    ingest_common_seed()
    out = transliterate('привет', 'Cyrl', 'Latn', language_id='lang:rus')
    assert out['ok'] is True
    assert out['profile']['language_id'] == 'lang:rus'


def test_transliteration_request_detects_script():
    init_db()
    ingest_common_seed()
    out = transliterate_request(TransliterationRequest(text='שלום', language_id='lang:heb', allow_detect=False))
    assert out['source_script'] == 'Hebr'
    assert out['result']


def test_upsert_transliteration_profile():
    init_db()
    ingest_common_seed()
    out = upsert_transliteration_profile('lang:eng', 'Latn', 'Latn', 'identity', 'production', example_in='hello', example_out='hello')
    assert out['ok'] is True
    listed = list_transliteration_profiles(language_id='lang:eng')
    assert any(r['scheme_name'] == 'identity' for r in listed['results'])


def test_low_resource_readiness_and_status_summary():
    init_db()
    ingest_common_seed()
    nav = get_language_readiness('lang:nav')
    cap = {r['capability_name']: r for r in nav['capabilities']}
    assert cap['translation']['maturity'] == 'experimental'
    status = get_system_status()
    assert status['graph']['counts']['transliteration_profiles'] >= 1
    assert any(r['capability_name'] == 'translation' for r in status['readiness_summary'])
