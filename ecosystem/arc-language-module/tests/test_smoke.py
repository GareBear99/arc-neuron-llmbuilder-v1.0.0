from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.detection import detect_language, detect_script
from arc_lang.services.lineage import get_lineage
from arc_lang.services.transliteration import transliterate
from arc_lang.services.translate_explain import translate_explain
from arc_lang.services.etymology import get_etymology
from arc_lang.core.models import TranslateExplainQuery


def setup_module(module):
    init_db()
    ingest_common_seed()


def test_detect_spanish():
    res = detect_language("hola gracias")
    assert res.winner_language_id == "lang:spa"


def test_detect_russian():
    res = detect_language("привет спасибо")
    assert res.winner_language_id == "lang:rus"


def test_detect_cherokee():
    res = detect_language("ᎣᏏᏲ")
    assert res.winner_language_id == "lang:chr"


def test_detect_bengali_script():
    assert detect_script("ধন্যবাদ") == "Beng"


def test_lineage_node_chain():
    res = get_lineage("lang:chr")
    assert res["ok"] is True
    assert any(n["node_type"] == "family" and n["name"] == "Iroquoian" for n in res["lineage_nodes"])


def test_transliterate_cyrillic():
    res = transliterate("привет", "Cyrl", "Latn")
    assert res["ok"] is True
    assert "privet" in res["result"].lower()


def test_translate_explain_seed_phrase():
    res = translate_explain(TranslateExplainQuery(text="hola", target_language_id="lang:eng"))
    assert res["ok"] is True
    assert res["translated_text"] == "hello"


def test_etymology_seed():
    res = get_etymology('lang:ita', 'ciao')
    assert res['ok'] is True
    assert any(p['parent']['language_id'] == 'lang:vec' for p in res['parents'])
