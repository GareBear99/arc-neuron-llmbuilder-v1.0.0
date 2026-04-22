CREATE TABLE IF NOT EXISTS self_fill_scan_runs (
    scan_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    language_ids_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_self_fill_scan_runs_created ON self_fill_scan_runs(created_at DESC);

CREATE TABLE IF NOT EXISTS self_fill_candidates (
    candidate_id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    language_id TEXT NOT NULL,
    surface_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_self_fill_candidates_scan ON self_fill_candidates(scan_id, status);
CREATE INDEX IF NOT EXISTS idx_self_fill_candidates_lang ON self_fill_candidates(language_id, surface_type, status);

CREATE TABLE IF NOT EXISTS self_fill_promotions (
    promotion_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    status TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_self_fill_promotions_candidate ON self_fill_promotions(candidate_id, created_at DESC);
