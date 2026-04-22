from __future__ import annotations
import sqlite3
from arc_lang.core.config import DB_PATH, SQL_INIT_PATH, SQL_DIR


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    # Run all SQL migrations in order
    migration_files = sorted(SQL_DIR.glob('*.sql'))
    with connect() as conn:
        for migration in migration_files:
            sql = migration.read_text(encoding='utf-8')
            conn.executescript(sql)
        conn.commit()
