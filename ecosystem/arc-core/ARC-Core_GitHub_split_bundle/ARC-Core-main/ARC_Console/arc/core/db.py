from __future__ import annotations
import sqlite3
from arc.core.config import DATA_DIR

DB_PATH = DATA_DIR / "arc_core.db"

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    subject TEXT NOT NULL,
    object TEXT,
    location TEXT,
    confidence REAL NOT NULL,
    severity INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_subject ON events(subject);
CREATE INDEX IF NOT EXISTS idx_events_object ON events(object);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_fingerprint ON events(fingerprint);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    aliases_json TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    risk_score REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id TEXT PRIMARY KEY,
    src_entity TEXT NOT NULL,
    dst_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_entity);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_entity);

CREATE TABLE IF NOT EXISTS watchlists (
    watchlist_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_entity_name ON watchlists(entity_id, name);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_events (
    case_event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    attached_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_case_event_unique ON case_events(case_id, event_id);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by_role TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    simulation_json TEXT NOT NULL,
    approved_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS receipt_chain (
    receipt_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    signature TEXT,
    key_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_receipt_ts ON receipt_chain(ts);
CREATE INDEX IF NOT EXISTS idx_receipt_record ON receipt_chain(record_type, record_id);

CREATE TABLE IF NOT EXISTS structures (
    structure_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    structure_type TEXT NOT NULL,
    levels INTEGER NOT NULL,
    polygon_json TEXT NOT NULL,
    center_lat REAL NOT NULL,
    center_lng REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_structure_identity ON structures(name, address);

CREATE TABLE IF NOT EXISTS sensors (
    sensor_id TEXT PRIMARY KEY,
    structure_id TEXT NOT NULL,
    label TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    reliability REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sensors_structure ON sensors(structure_id);

CREATE TABLE IF NOT EXISTS geofences (
    geofence_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    geofence_type TEXT NOT NULL,
    structure_id TEXT,
    polygon_json TEXT NOT NULL,
    severity INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS track_points (
    track_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    subject TEXT NOT NULL,
    structure_id TEXT NOT NULL,
    source TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    confidence REAL NOT NULL,
    zone TEXT NOT NULL,
    floor INTEGER,
    observations_json TEXT NOT NULL,
    estimate_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_track_subject ON track_points(subject);
CREATE INDEX IF NOT EXISTS idx_track_ts ON track_points(ts);
CREATE INDEX IF NOT EXISTS idx_track_structure ON track_points(structure_id, ts DESC);

CREATE TABLE IF NOT EXISTS blueprint_overlays (
    overlay_id TEXT PRIMARY KEY,
    structure_id TEXT NOT NULL,
    name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    opacity REAL NOT NULL,
    scale REAL NOT NULL,
    offset_x REAL NOT NULL,
    offset_y REAL NOT NULL,
    rotation_deg REAL NOT NULL,
    floor INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_overlay_structure ON blueprint_overlays(structure_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_overlay_identity ON blueprint_overlays(structure_id, name, ifnull(floor, -1));

CREATE TABLE IF NOT EXISTS calibration_profiles (
    profile_id TEXT PRIMARY KEY,
    structure_id TEXT NOT NULL,
    name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_calibration_structure ON calibration_profiles(structure_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_calibration_identity ON calibration_profiles(structure_id, name);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    subject TEXT,
    structure_id TEXT,
    detail_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incident_ts ON incidents(ts);

CREATE TABLE IF NOT EXISTS auth_users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    created_from TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS connector_sources (
    connector_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    connector_type TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    cursor_value TEXT,
    last_polled_at TEXT,
    last_result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_connector_name ON connector_sources(name);

CREATE TABLE IF NOT EXISTS connector_runs (
    run_id TEXT PRIMARY KEY,
    connector_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    imported_count INTEGER NOT NULL DEFAULT 0,
    detail_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyst_notes (
    note_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_subject ON analyst_notes(subject_type, subject_id, created_at DESC);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
