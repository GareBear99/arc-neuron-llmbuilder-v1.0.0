CREATE TABLE IF NOT EXISTS self_fill_replay_runs (
  replay_run_id TEXT PRIMARY KEY,
  release_run_id TEXT NOT NULL,
  rollback_id TEXT,
  replay_manifest_path TEXT NOT NULL,
  replay_status TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_fill_compaction_actions (
  compaction_id TEXT PRIMARY KEY,
  release_run_id TEXT NOT NULL,
  retention_class TEXT NOT NULL,
  compact_bundle_path TEXT NOT NULL,
  compact_sha256 TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
