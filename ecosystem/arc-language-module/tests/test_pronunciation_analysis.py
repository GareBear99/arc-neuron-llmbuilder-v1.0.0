from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.pronunciation import pronunciation_guide, list_pronunciation_profiles
from arc_lang.services.linguistic_analysis import analyze_text
from arc_lang.core.models import PronunciationRequest, AnalysisRequest
from arc_lang.services.translate_explain import translate_explain
from arc_lang.core.models import TranslateExplainQuery


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_pronunciation_hint_for_russian():
    result = pronunciation_guide(PronunciationRequest(text='привет', language_id='lang:rus'))
    assert result['ok'] is True
    assert result['pronunciation_text']
    assert result['source_script'] == 'Cyrl'


def test_pronunciation_profile_listing():
    result = list_pronunciation_profiles(language_id='lang:spa')
    assert result['ok'] is True
    assert result['results']
    assert result['results'][0]['language_id'] == 'lang:spa'


def test_analyze_text_for_seeded_phrase():
    result = analyze_text(AnalysisRequest(text='hola', language_id='lang:spa'))
    assert result['ok'] is True
    assert result['token_count'] == 1
    assert result['phrase_match']['canonical_key'] == 'hello'
    assert result['pronunciation']['ok'] is True


def test_translate_explain_includes_analysis_and_target_pronunciation():
    result = translate_explain(TranslateExplainQuery(text='hola', target_language_id='lang:eng', source_language_id='lang:spa'))
    assert result['ok'] is True
    assert result['source_analysis']['ok'] is True
    assert result['target_pronunciation']['ok'] is True
