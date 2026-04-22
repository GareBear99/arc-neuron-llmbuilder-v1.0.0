CREATE TABLE IF NOT EXISTS self_fill_retention_policies (
  policy_id TEXT PRIMARY KEY,
  policy_name TEXT UNIQUE NOT NULL,
  schedule_kind TEXT NOT NULL,
  retention_class TEXT NOT NULL,
  keep_days INTEGER,
  keep_count INTEGER,
  compact_after_days INTEGER,
  enabled INTEGER NOT NULL DEFAULT 1,
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_fill_retention_actions (
  action_id TEXT PRIMARY KEY,
  release_run_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  retention_class TEXT NOT NULL,
  action_kind TEXT NOT NULL,
  action_status TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(release_run_id) REFERENCES self_fill_release_runs(release_run_id),
  FOREIGN KEY(policy_id) REFERENCES self_fill_retention_policies(policy_id)
);

CREATE TABLE IF NOT EXISTS self_fill_rollback_index (
  rollback_id TEXT PRIMARY KEY,
  release_run_id TEXT UNIQUE NOT NULL,
  retention_class TEXT NOT NULL,
  replay_priority INTEGER NOT NULL,
  manifest_path TEXT NOT NULL,
  archive_path TEXT NOT NULL,
  ledger_path TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  index_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(release_run_id) REFERENCES self_fill_release_runs(release_run_id)
);
