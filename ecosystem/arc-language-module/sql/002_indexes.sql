-- Migration 002: Performance indexes and production hardening
-- Safe to re-run: all statements use IF NOT EXISTS / ON CONFLICT IGNORE

-- ── Composite indexes for common query patterns ──────────────────────────

-- Coverage report: per-language profile lookups
CREATE INDEX IF NOT EXISTS idx_pronunciation_profiles_lang_kind
    ON pronunciation_profiles(language_id, profile_kind);

CREATE INDEX IF NOT EXISTS idx_phonology_profiles_lang_notation
    ON phonology_profiles(language_id, notation_system);

-- Concept lookup: target-type + target-id (used in coverage, bundle queries)
CREATE INDEX IF NOT EXISTS idx_concept_links_target_lang
    ON concept_links(target_type, target_id)
    WHERE target_type = 'language';

CREATE INDEX IF NOT EXISTS idx_concept_links_target_phrase
    ON concept_links(target_type, target_id)
    WHERE target_type = 'phrase_key';

-- Variant lookup by language + type
CREATE INDEX IF NOT EXISTS idx_language_variants_lang_type
    ON language_variants(language_id, variant_type, status);

-- Alias lookup by type (for coverage alias_by_type breakdown)
CREATE INDEX IF NOT EXISTS idx_language_aliases_lang_type
    ON language_aliases(language_id, alias_type);

-- Provenance lookup by source (for import conflict detection)
CREATE INDEX IF NOT EXISTS idx_provenance_source
    ON provenance_records(source_name, record_type);

-- Translation backend: source+target language pair lookups
CREATE INDEX IF NOT EXISTS idx_phrase_translations_canonical_key
    ON phrase_translations(canonical_key, register);

-- Lexeme full-text lookup support
CREATE INDEX IF NOT EXISTS idx_lexemes_lemma_lower
    ON lexemes(lower(lemma), language_id);

-- Etymology traversal
CREATE INDEX IF NOT EXISTS idx_etymology_parent
    ON etymology_edges(parent_lexeme_id);

-- Relationship assertions: both directions
CREATE INDEX IF NOT EXISTS idx_relationship_assertions_relation
    ON relationship_assertions(relation, confidence);

-- Acquisition workspace: status filtering
CREATE INDEX IF NOT EXISTS idx_acquisition_jobs_status
    ON acquisition_jobs(acquisition_status, created_at);

CREATE INDEX IF NOT EXISTS idx_staged_assets_status
    ON staged_assets(status, job_id);

-- Governance: pending review queries
CREATE INDEX IF NOT EXISTS idx_language_submissions_lang_status
    ON language_submissions(language_id, status);

CREATE INDEX IF NOT EXISTS idx_custom_lineage_status_conf
    ON custom_lineage_assertions(status, confidence);

-- Provider health: latest-per-provider query
CREATE INDEX IF NOT EXISTS idx_provider_health_name_time
    ON provider_health(provider_name, created_at DESC);

-- Runtime receipts: recent receipts
CREATE INDEX IF NOT EXISTS idx_job_receipts_status_time
    ON job_receipts(status, created_at DESC);

-- Install plans: by pair
CREATE INDEX IF NOT EXISTS idx_install_plans_pair
    ON translation_install_plans(source_language_id, target_language_id, provider_name);

-- Source weights: frequently joined in arbitration
CREATE INDEX IF NOT EXISTS idx_source_weights_name
    ON source_weights(source_name, authority_weight);

-- Coverage reports: recent
CREATE INDEX IF NOT EXISTS idx_coverage_reports_time
    ON coverage_reports(created_at DESC);

-- Implementation matrix: recent
CREATE INDEX IF NOT EXISTS idx_impl_matrix_time
    ON implementation_matrix_reports(created_at DESC);
