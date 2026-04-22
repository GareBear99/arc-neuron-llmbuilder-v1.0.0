from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
SQL_DIR = ROOT / "sql"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "arc_language.db"
SQL_INIT_PATH = SQL_DIR / "001_init.sql"
SEED_PATH = CONFIG_DIR / "common_languages_seed.json"
PHRASE_PATH = CONFIG_DIR / "common_phrases_seed.json"

SOURCE_MANIFEST_PATH = CONFIG_DIR / "source_manifests.json"

ETYMOLOGY_SEED_PATH = CONFIG_DIR / "common_etymologies_seed.json"

TRANSLITERATION_SEED_PATH = CONFIG_DIR / 'transliteration_seed.json'

PHONOLOGY_SEED_PATH = CONFIG_DIR / 'phonology_seed.json'
BACKEND_MANIFEST_PATH = CONFIG_DIR / 'backend_manifests.json'
CORPUS_MANIFEST_PATH = CONFIG_DIR / 'corpus_manifests.json'
VARIANTS_SEED_PATH = CONFIG_DIR / 'variants_seed.json'
CONCEPTS_SEED_PATH = CONFIG_DIR / 'concepts_seed.json'
INGESTION_WORKSPACE_DIR = ROOT / 'workspace'
INGESTION_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
