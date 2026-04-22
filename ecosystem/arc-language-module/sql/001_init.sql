PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS scripts (
    script_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unicode_ranges_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_node_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_type ON lineage_nodes(node_type, name);

CREATE TABLE IF NOT EXISTS languages (
    language_id TEXT PRIMARY KEY,
    iso639_3 TEXT,
    name TEXT NOT NULL,
    family TEXT,
    branch TEXT,
    parent_language_id TEXT,
    family_node_id TEXT,
    branch_node_id TEXT,
    parent_node_id TEXT,
    aliases_json TEXT NOT NULL,
    common_words_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_languages_iso ON languages(iso639_3);
CREATE INDEX IF NOT EXISTS idx_languages_name ON languages(name);

CREATE TABLE IF NOT EXISTS language_scripts (
    language_id TEXT NOT NULL,
    script_id TEXT NOT NULL,
    PRIMARY KEY (language_id, script_id)
);

CREATE TABLE IF NOT EXISTS lineage_edges (
    edge_id TEXT PRIMARY KEY,
    src_id TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    disputed INTEGER NOT NULL DEFAULT 0,
    source_ref TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lineage_src ON lineage_edges(src_id);
CREATE INDEX IF NOT EXISTS idx_lineage_dst ON lineage_edges(dst_id);

CREATE TABLE IF NOT EXISTS translation_assertions (
    assertion_id TEXT PRIMARY KEY,
    source_language_id TEXT,
    target_language_id TEXT,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phrase_translations (
    phrase_id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL,
    language_id TEXT NOT NULL,
    text_value TEXT NOT NULL,
    register TEXT NOT NULL DEFAULT 'general',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_phrase_key_lang ON phrase_translations(canonical_key, language_id);

CREATE TABLE IF NOT EXISTS lexemes (
    lexeme_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    lemma TEXT NOT NULL,
    gloss TEXT,
    canonical_meaning_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lexemes_lang_lemma ON lexemes(language_id, lemma);

CREATE TABLE IF NOT EXISTS etymology_edges (
    etymology_id TEXT PRIMARY KEY,
    child_lexeme_id TEXT NOT NULL,
    parent_lexeme_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_ref TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_etym_child ON etymology_edges(child_lexeme_id);

CREATE TABLE IF NOT EXISTS provenance_records (
    provenance_id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    confidence REAL NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prov_record ON provenance_records(record_type, record_id);

CREATE TABLE IF NOT EXISTS import_runs (
    import_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    file_path TEXT,
    records_seen INTEGER NOT NULL,
    records_upserted INTEGER NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_import_runs_source ON import_runs(source_name, created_at);

CREATE TABLE IF NOT EXISTS custom_lineage_assertions (
    assertion_id TEXT PRIMARY KEY,
    src_id TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    disputed INTEGER NOT NULL DEFAULT 0,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    notes TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_custom_lineage_src ON custom_lineage_assertions(src_id);
CREATE INDEX IF NOT EXISTS idx_custom_lineage_dst ON custom_lineage_assertions(dst_id);
CREATE INDEX IF NOT EXISTS idx_custom_lineage_status ON custom_lineage_assertions(status);

CREATE TABLE IF NOT EXISTS language_submissions (
    submission_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    iso639_3 TEXT,
    name TEXT NOT NULL,
    family TEXT,
    branch TEXT,
    parent_language_id TEXT,
    aliases_json TEXT NOT NULL,
    common_words_json TEXT NOT NULL,
    scripts_json TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    confidence REAL NOT NULL,
    notes TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_language_submissions_status ON language_submissions(status);
CREATE INDEX IF NOT EXISTS idx_language_submissions_lang ON language_submissions(language_id);

CREATE TABLE IF NOT EXISTS review_decisions (
    review_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    confidence REAL NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_target ON review_decisions(target_type, target_id, created_at);

CREATE TABLE IF NOT EXISTS language_capabilities (
    capability_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    maturity TEXT NOT NULL,
    confidence REAL NOT NULL,
    provider TEXT NOT NULL,
    notes TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_language_capability_unique ON language_capabilities(language_id, capability_name, provider);

CREATE TABLE IF NOT EXISTS provider_registry (
    provider_name TEXT PRIMARY KEY,
    provider_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    local_only INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_provider_registry_type ON provider_registry(provider_type, provider_name);

CREATE TABLE IF NOT EXISTS provider_health (
    health_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER,
    error_rate REAL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_provider_health_provider ON provider_health(provider_name, created_at);

CREATE TABLE IF NOT EXISTS job_receipts (
    receipt_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    provider_name TEXT,
    status TEXT NOT NULL,
    request_payload_json TEXT NOT NULL,
    response_payload_json TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_receipts_lookup ON job_receipts(job_type, provider_name, created_at);

CREATE TABLE IF NOT EXISTS translation_install_plans (
    plan_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    source_language_id TEXT NOT NULL,
    target_language_id TEXT NOT NULL,
    readiness TEXT NOT NULL,
    next_action TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    missing_json TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_translation_install_plans_lookup ON translation_install_plans(provider_name, source_language_id, target_language_id, created_at);


CREATE TABLE IF NOT EXISTS provider_action_receipts (
    action_receipt_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    action_name TEXT NOT NULL,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 1,
    allow_mutation INTEGER NOT NULL DEFAULT 0,
    request_payload_json TEXT NOT NULL,
    response_payload_json TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_provider_action_receipts_lookup ON provider_action_receipts(provider_name, action_name, created_at);


CREATE TABLE IF NOT EXISTS operator_policies (
    policy_key TEXT PRIMARY KEY,
    policy_value TEXT NOT NULL,
    notes TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_exports (
    export_id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    include_receipts INTEGER NOT NULL DEFAULT 1,
    include_runtime INTEGER NOT NULL DEFAULT 1,
    include_graph INTEGER NOT NULL DEFAULT 1,
    language_ids_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_exports_created ON evidence_exports(created_at);


CREATE TABLE IF NOT EXISTS pronunciation_profiles (
    profile_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    profile_kind TEXT NOT NULL,
    romanization_scheme TEXT,
    ipa_hint TEXT,
    examples_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pronunciation_profiles_lang ON pronunciation_profiles(language_id, profile_kind);


CREATE TABLE IF NOT EXISTS transliteration_profiles (
    profile_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    source_script TEXT NOT NULL,
    target_script TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    coverage TEXT NOT NULL,
    example_in TEXT,
    example_out TEXT,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transliteration_profiles_lang ON transliteration_profiles(language_id, source_script, target_script);

CREATE TABLE IF NOT EXISTS language_aliases (
    alias_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    normalized_form TEXT,
    alias_type TEXT NOT NULL,
    script_id TEXT,
    region_hint TEXT,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    confidence REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_language_aliases_lang ON language_aliases(language_id);
CREATE INDEX IF NOT EXISTS idx_language_aliases_alias ON language_aliases(alias);

CREATE TABLE IF NOT EXISTS relationship_assertions (
    assertion_id TEXT PRIMARY KEY,
    src_lexeme_id TEXT NOT NULL,
    dst_lexeme_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    disputed INTEGER NOT NULL DEFAULT 0,
    source_name TEXT NOT NULL,
    source_ref TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_relationship_src ON relationship_assertions(src_lexeme_id);
CREATE INDEX IF NOT EXISTS idx_relationship_dst ON relationship_assertions(dst_lexeme_id);

CREATE TABLE IF NOT EXISTS batch_io_runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    object_type TEXT NOT NULL,
    path TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 1,
    record_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    notes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_weights (
    source_name TEXT PRIMARY KEY,
    authority_weight REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS semantic_concepts (
    concept_id TEXT PRIMARY KEY,
    canonical_label TEXT NOT NULL,
    domain TEXT NOT NULL DEFAULT 'general',
    description TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT 'user_custom',
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 0.8,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_semantic_concepts_label ON semantic_concepts(canonical_label, domain);

CREATE TABLE IF NOT EXISTS concept_links (
    link_id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL DEFAULT 'expresses',
    confidence REAL NOT NULL DEFAULT 0.8,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_concept_links_concept ON concept_links(concept_id, target_type);
CREATE INDEX IF NOT EXISTS idx_concept_links_target ON concept_links(target_type, target_id);

CREATE TABLE IF NOT EXISTS language_variants (
    variant_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    variant_name TEXT NOT NULL,
    variant_type TEXT NOT NULL,
    region_hint TEXT,
    script_id TEXT,
    status TEXT NOT NULL DEFAULT 'documented',
    mutual_intelligibility REAL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_language_variants_lang ON language_variants(language_id, variant_type);

CREATE TABLE IF NOT EXISTS conflict_review_exports (
    export_id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    language_ids_json TEXT NOT NULL,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conflict_review_exports_created ON conflict_review_exports(created_at);

CREATE TABLE IF NOT EXISTS coverage_reports (
    report_id TEXT PRIMARY KEY,
    output_path TEXT,
    language_ids_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_coverage_reports_created ON coverage_reports(created_at);

CREATE TABLE IF NOT EXISTS phonology_profiles (
    profile_id TEXT PRIMARY KEY,
    language_id TEXT NOT NULL,
    notation_system TEXT NOT NULL,
    broad_ipa TEXT,
    stress_policy TEXT,
    syllable_template TEXT,
    examples_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backend_manifests (
    manifest_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    backend_kind TEXT NOT NULL,
    execution_mode TEXT NOT NULL,
    supported_pairs_json TEXT NOT NULL DEFAULT '[]',
    dependency_json TEXT NOT NULL DEFAULT '[]',
    health_policy_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corpus_manifests (
    manifest_id TEXT PRIMARY KEY,
    corpus_name TEXT NOT NULL,
    corpus_kind TEXT NOT NULL,
    coverage_scope TEXT NOT NULL,
    languages_json TEXT NOT NULL DEFAULT '[]',
    source_name TEXT NOT NULL DEFAULT 'local',
    license_ref TEXT,
    acquisition_status TEXT NOT NULL DEFAULT 'external_required',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS implementation_matrix_reports (
    report_id TEXT PRIMARY KEY,
    output_path TEXT,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS acquisition_jobs (
    job_id TEXT PRIMARY KEY,
    corpus_name TEXT NOT NULL,
    corpus_kind TEXT,
    stage_name TEXT NOT NULL,
    output_dir TEXT,
    acquisition_status TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_acquisition_jobs_corpus ON acquisition_jobs(corpus_name, created_at);

CREATE TABLE IF NOT EXISTS staged_assets (
    asset_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    asset_kind TEXT NOT NULL,
    file_size_bytes INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_staged_assets_job ON staged_assets(job_id, created_at);

CREATE TABLE IF NOT EXISTS validation_reports (
    report_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    expected_kind TEXT NOT NULL,
    expected_source_name TEXT,
    detected_kind TEXT,
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_validation_reports_file ON validation_reports(file_path, created_at);

CREATE TABLE IF NOT EXISTS ingestion_workspace_exports (
    export_id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingestion_workspace_exports_created ON ingestion_workspace_exports(created_at);
