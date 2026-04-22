from __future__ import annotations
from arc_lang.core.db import connect


def get_graph_stats() -> dict:
    """Return counts for all 41 tracked database tables as a single stats dict."""
    tables = {
        # Core language graph
        'languages': 'languages',
        'scripts': 'scripts',
        'language_scripts': 'language_scripts',
        'lineage_nodes': 'lineage_nodes',
        'lineage_edges': 'lineage_edges',
        # Lexical / phrase graph
        'phrase_translations': 'phrase_translations',
        'lexemes': 'lexemes',
        'etymology_edges': 'etymology_edges',
        # Aliases and relationships
        'language_aliases': 'language_aliases',
        'relationship_assertions': 'relationship_assertions',
        # Variants and concepts
        'language_variants': 'language_variants',
        'semantic_concepts': 'semantic_concepts',
        'concept_links': 'concept_links',
        # Linguistic profiles
        'pronunciation_profiles': 'pronunciation_profiles',
        'phonology_profiles': 'phonology_profiles',
        'transliteration_profiles': 'transliteration_profiles',
        # Governance
        'language_submissions': 'language_submissions',
        'custom_lineage_assertions': 'custom_lineage_assertions',
        'review_decisions': 'review_decisions',
        'language_capabilities': 'language_capabilities',
        # Provenance and imports
        'provenance_records': 'provenance_records',
        'import_runs': 'import_runs',
        'batch_io_runs': 'batch_io_runs',
        'source_weights': 'source_weights',
        # Runtime and providers
        'providers': 'provider_registry',
        'provider_health': 'provider_health',
        'job_receipts': 'job_receipts',
        'provider_action_receipts': 'provider_action_receipts',
        'translation_install_plans': 'translation_install_plans',
        # Manifests and matrix
        'backend_manifests': 'backend_manifests',
        'corpus_manifests': 'corpus_manifests',
        'implementation_matrix_reports': 'implementation_matrix_reports',
        # Acquisition workspace
        'acquisition_jobs': 'acquisition_jobs',
        'staged_assets': 'staged_assets',
        'validation_reports': 'validation_reports',
        # Exports and reports
        'evidence_exports': 'evidence_exports',
        'conflict_review_exports': 'conflict_review_exports',
        'coverage_reports': 'coverage_reports',
        'ingestion_workspace_exports': 'ingestion_workspace_exports',
        # Policy and assertions
        'operator_policies': 'operator_policies',
        'translation_assertions': 'translation_assertions',
    }
    counts = {}
    with connect() as conn:
        for key, table in tables.items():
            counts[key] = conn.execute(f'SELECT COUNT(*) AS c FROM {table}').fetchone()['c']
    return {'ok': True, 'counts': counts}

