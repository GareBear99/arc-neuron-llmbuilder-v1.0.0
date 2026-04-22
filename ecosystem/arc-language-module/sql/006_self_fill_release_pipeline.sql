CREATE TABLE IF NOT EXISTS self_fill_release_runs (
    release_run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    manifest_path TEXT,
    signature_path TEXT,
    ledger_path TEXT,
    archive_path TEXT,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_fill_release_artifacts (
    artifact_id TEXT PRIMARY KEY,
    release_run_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes_size INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (release_run_id) REFERENCES self_fill_release_runs(release_run_id)
);
