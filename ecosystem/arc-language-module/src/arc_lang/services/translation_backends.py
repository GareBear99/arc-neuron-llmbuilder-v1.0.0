from __future__ import annotations

import importlib.util
from arc_lang.core.db import connect
from arc_lang.core.models import RuntimeTranslateRequest, TranslateExplainQuery
from arc_lang.services.translate_explain import translate_explain

ISO6393_TO_RUNTIME = {
    # Major world languages
    'eng': 'en', 'spa': 'es', 'fra': 'fr', 'deu': 'de', 'ita': 'it', 'por': 'pt',
    'rus': 'ru', 'ukr': 'uk', 'jpn': 'ja', 'kor': 'ko',
    'hin': 'hi', 'ben': 'bn', 'mar': 'mr', 'urd': 'ur', 'tam': 'ta', 'tel': 'te',
    'pan': 'pa', 'heb': 'he', 'tha': 'th', 'nld': 'nl', 'pol': 'pl', 'tur': 'tr',
    'vie': 'vi', 'ind': 'id',
    # Seeded language-specific ISO codes
    'arb': 'ar',   # Arabic (Modern Standard) — iso arb, runtime code ar
    'cmn': 'zh',   # Mandarin Chinese — iso cmn, runtime code zh
    'yue': 'yue',  # Cantonese — iso yue, runtime code yue (limited Argos support)
    'fas': 'fa',   # Persian/Farsi
    'msa': 'ms',   # Malay
    'swa': 'sw',   # Swahili
    'amh': 'am',   # Amharic
    # Low-resource / Indigenous — runtime codes exist but Argos coverage is absent
    'nav': 'nav',  # Navajo — no known Argos package; runtime stub only
    'chr': 'chr',  # Cherokee — no known Argos package; runtime stub only
    'crk': 'crk',  # Plains Cree — no known Argos package; runtime stub only
    'ell': 'el',   # Greek (Modern)
}


def _language_codes(language_id: str) -> dict:
    """Return language code information (language_id, iso639_3, runtime_code, name) for a language."""
    with connect() as conn:
        row = conn.execute(
            "SELECT language_id, iso639_3, name FROM languages WHERE language_id = ?",
            (language_id,),
        ).fetchone()
    if not row:
        return {'language_id': language_id, 'iso639_3': None, 'runtime_code': None, 'name': None}
    iso3 = row['iso639_3']
    return {
        'language_id': row['language_id'],
        'iso639_3': iso3,
        'runtime_code': ISO6393_TO_RUNTIME.get(iso3) or iso3,
        'name': row['name'],
    }


def _argostranslate_available() -> bool:
    """Return True if the argostranslate library is installed."""
    return importlib.util.find_spec('argostranslate') is not None


class TranslationBackend:
    name = 'base'

    def translate(self, req: RuntimeTranslateRequest, source_language_id: str) -> dict:
        """Execute a translation request through this backend adapter and return the result dict."""
        raise NotImplementedError


class LocalSeedTranslationBackend(TranslationBackend):
    name = 'local_seed'

    def translate(self, req: RuntimeTranslateRequest, source_language_id: str) -> dict:
        """Execute a translation through this backend and return a result dict with ok, provider, translation, and notes."""
        result = translate_explain(TranslateExplainQuery(
            text=req.text,
            source_language_id=source_language_id,
            target_language_id=req.target_language_id,
            allow_detect=False,
        ))
        if result.get('ok'):
            return {
                'ok': True,
                'mode': 'backend_local_seed',
                'provider': self.name,
                'translation': result,
                'notes': ['Resolved by local seeded phrase/lexeme graph.'],
            }
        return {
            'ok': False,
            'provider': self.name,
            'error': result.get('error', 'local_seed_unresolved'),
            'backend_response': result,
            'notes': ['Local seeded graph could not resolve this translation.'],
        }


class MirrorTranslationBackend(TranslationBackend):
    name = 'mirror_mock'

    def translate(self, req: RuntimeTranslateRequest, source_language_id: str) -> dict:
        """Execute a translation through this backend and return a result dict with ok, provider, translation, and notes."""
        if source_language_id != req.target_language_id:
            return {
                'ok': False,
                'provider': self.name,
                'error': 'mirror_requires_same_language',
                'notes': ['mirror_mock only supports same-language echo/mirror behavior.'],
            }
        return {
            'ok': True,
            'mode': 'backend_mirror_mock',
            'provider': self.name,
            'translation': {
                'ok': True,
                'mode': 'mirror_same_language',
                'source_language_id': source_language_id,
                'target_language_id': req.target_language_id,
                'source_text': req.text,
                'translated_text': req.text,
                'register': 'identity',
                'provenance': [],
                'rationale': 'Mirror backend returned same-language identity output.',
            },
            'notes': ['Useful for dry pipeline verification and same-language normalization tests.'],
        }


class ArgosLocalTranslationBackend(TranslationBackend):
    name = 'argos_local'

    def translate(self, req: RuntimeTranslateRequest, source_language_id: str) -> dict:
        """Execute a translation through this backend and return a result dict with ok, provider, translation, and notes."""
        if not _argostranslate_available():
            return {
                'ok': False,
                'provider': self.name,
                'error': 'translation_backend_dependency_missing',
                'dependency': 'argostranslate',
                'notes': ['Install argostranslate plus matching language packages to enable local execution.'],
            }
        src = _language_codes(source_language_id)
        dst = _language_codes(req.target_language_id)
        if not src['runtime_code'] or not dst['runtime_code']:
            return {
                'ok': False,
                'provider': self.name,
                'error': 'translation_backend_language_code_unmapped',
                'source_language': src,
                'target_language': dst,
                'notes': ['No runtime mapping exists from internal language ID to Argos language code.'],
            }
        try:
            from argostranslate import translate as argos_translate
            installed = argos_translate.get_installed_languages()
        except Exception as e:
            return {
                'ok': False,
                'provider': self.name,
                'error': 'translation_backend_dependency_failed',
                'notes': [f'argostranslate import/runtime failed: {type(e).__name__}: {e}'],
            }

        source_lang = next((l for l in installed if getattr(l, 'code', None) == src['runtime_code']), None)
        target_lang = next((l for l in installed if getattr(l, 'code', None) == dst['runtime_code']), None)
        if not source_lang or not target_lang:
            return {
                'ok': False,
                'provider': self.name,
                'error': 'translation_backend_language_pair_missing',
                'source_language': src,
                'target_language': dst,
                'installed_codes': sorted([getattr(l, 'code', None) for l in installed if getattr(l, 'code', None)]),
                'notes': ['Argos runtime is installed, but the requested source/target package pair is not available locally.'],
            }
        try:
            translation_obj = source_lang.get_translation(target_lang)
            if translation_obj is None:
                return {
                    'ok': False,
                    'provider': self.name,
                    'error': 'translation_backend_language_pair_missing',
                    'source_language': src,
                    'target_language': dst,
                    'notes': ['Argos source/target languages are present, but no direct translation package was found.'],
                }
            translated_text = translation_obj.translate(req.text)
        except Exception as e:
            return {
                'ok': False,
                'provider': self.name,
                'error': 'translation_backend_runtime_failed',
                'source_language': src,
                'target_language': dst,
                'notes': [f'Argos runtime translation failed: {type(e).__name__}: {e}'],
            }

        return {
            'ok': True,
            'mode': 'backend_argos_local',
            'provider': self.name,
            'translation': {
                'ok': True,
                'mode': 'argos_local_translate',
                'source_language_id': source_language_id,
                'target_language_id': req.target_language_id,
                'source_text': req.text,
                'translated_text': translated_text,
                'register': 'general',
                'provenance': [
                    {'source_name': 'argostranslate', 'source_ref': f"{src['runtime_code']}->{dst['runtime_code']}", 'confidence': 0.7, 'notes': 'Optional local Argos Translate backend execution.'}
                ],
                'rationale': 'Translated by optional local Argos backend adapter.',
            },
            'dispatch_payload': {
                'source_runtime_code': src['runtime_code'],
                'target_runtime_code': dst['runtime_code'],
                'dry_run': req.dry_run,
            },
            'notes': ['Executed through optional local Argos Translate backend.'],
        }


class BoundaryStubTranslationBackend(TranslationBackend):
    def __init__(self, name: str):
        self.name = name

    def translate(self, req: RuntimeTranslateRequest, source_language_id: str) -> dict:
        """Execute a translation through this backend and return a result dict with ok, provider, translation, and notes."""
        payload = {
            'provider': self.name,
            'source_language_id': source_language_id,
            'target_language_id': req.target_language_id,
            'text': req.text,
            'voice_hint': req.voice_hint,
        }
        if req.dry_run:
            return {
                'ok': True,
                'mode': 'backend_boundary_dry_run',
                'provider': self.name,
                'translation': {
                    'ok': True,
                    'mode': 'boundary_stub',
                    'source_language_id': source_language_id,
                    'target_language_id': req.target_language_id,
                    'source_text': req.text,
                    'translated_text': None,
                    'register': 'unresolved',
                    'provenance': [],
                    'rationale': f'{self.name} boundary accepted the request in dry-run mode.',
                },
                'dispatch_payload': payload,
                'notes': [
                    f'{self.name} is wired as a backend boundary stub.',
                    'Provide a live adapter/runtime bridge to execute actual remote translation.',
                ],
            }
        return {
            'ok': False,
            'provider': self.name,
            'error': 'translation_backend_live_bridge_missing',
            'dispatch_payload': payload,
            'notes': [
                f'{self.name} boundary exists, but no live runtime bridge is configured in this package.',
            ],
        }


BUILTIN_TRANSLATION_BACKENDS = {
    'local_seed': LocalSeedTranslationBackend,
    'mirror_mock': MirrorTranslationBackend,
    'argos_local': ArgosLocalTranslationBackend,
    'argos_bridge': lambda: BoundaryStubTranslationBackend('argos_bridge'),
    'nllb_bridge': lambda: BoundaryStubTranslationBackend('nllb_bridge'),
}


def get_translation_backend(name: str | None) -> TranslationBackend | None:
    """Return a TranslationBackend instance by provider name, or None."""
    if not name:
        return None
    factory = BUILTIN_TRANSLATION_BACKENDS.get(name)
    if not factory:
        return None
    return factory()


def list_builtin_translation_backends() -> dict:
    """List all built-in translation backends with their kind, live_execution status, and dependency notes."""
    argos_available = _argostranslate_available()
    return {
        'ok': True,
        'backends': [
            {'provider_name': 'local_seed', 'kind': 'local', 'live_execution': True, 'optional_dependency': None, 'notes': 'Seeded graph-backed phrase/lexeme translation.'},
            {'provider_name': 'mirror_mock', 'kind': 'local', 'live_execution': True, 'optional_dependency': None, 'notes': 'Same-language mirror backend for pipeline validation.'},
            {'provider_name': 'argos_local', 'kind': 'local_optional', 'live_execution': argos_available, 'optional_dependency': 'argostranslate', 'notes': 'Optional offline local Argos Translate adapter when the dependency and language packages are installed.'},
            {'provider_name': 'argos_bridge', 'kind': 'boundary', 'live_execution': False, 'optional_dependency': None, 'notes': 'Boundary stub alias for future/live Argos bridge integration.'},
            {'provider_name': 'nllb_bridge', 'kind': 'boundary', 'live_execution': False, 'optional_dependency': None, 'notes': 'Bridge stub for a future NLLB-style adapter.'},
        ],
    }
