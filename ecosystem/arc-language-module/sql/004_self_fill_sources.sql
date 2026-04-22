CREATE TABLE IF NOT EXISTS self_fill_import_runs (
    import_run_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    scan_id TEXT NOT NULL,
    records_seen INTEGER NOT NULL,
    candidates_staged INTEGER NOT NULL,
    conflict_count INTEGER NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_self_fill_import_runs_created ON self_fill_import_runs(created_at DESC);

CREATE TABLE IF NOT EXISTS self_fill_conflicts (
    conflict_id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    candidate_id TEXT,
    language_id TEXT,
    surface_type TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    existing_ref TEXT,
    incoming_ref TEXT,
    details_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_self_fill_conflicts_scan ON self_fill_conflicts(scan_id, status);
