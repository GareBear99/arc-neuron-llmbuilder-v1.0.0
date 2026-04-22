CREATE TABLE IF NOT EXISTS self_fill_arbitration_runs (
    arbitration_run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    language_ids_json TEXT NOT NULL DEFAULT '[]',
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_fill_arbitration_decisions (
    decision_id TEXT PRIMARY KEY,
    arbitration_run_id TEXT NOT NULL REFERENCES self_fill_arbitration_runs(arbitration_run_id) ON DELETE CASCADE,
    language_id TEXT NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    surface_type TEXT NOT NULL,
    group_key TEXT NOT NULL,
    winning_candidate_id TEXT,
    winning_score REAL,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_self_fill_arb_runs_created
    ON self_fill_arbitration_runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_self_fill_arb_decisions_run
    ON self_fill_arbitration_decisions(arbitration_run_id, language_id, surface_type);
