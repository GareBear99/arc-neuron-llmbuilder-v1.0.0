from __future__ import annotations

from pathlib import Path
import tomllib

from arc_lang.services.stats import get_graph_stats
from arc_lang.version import VERSION


def get_release_snapshot() -> dict:
    """Return release-integrity metadata and live seeded graph counts for packaging/audit use."""
    project_root = Path(__file__).resolve().parents[3]
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_version = pyproject["project"]["version"]
    api_app_text = (project_root / "src" / "arc_lang" / "api" / "app.py").read_text(encoding="utf-8")
    api_router_text = (project_root / "src" / "arc_lang" / "api" / "routers" / "core.py").read_text(encoding="utf-8")
    graph_counts = get_graph_stats().get("counts", {})
    checks = {
        "package_matches_pyproject": VERSION == pyproject_version,
        "api_app_uses_version_constant": "version=VERSION" in api_app_text,
        "health_route_uses_version_constant": "'version': VERSION" in api_router_text or '"version": VERSION' in api_router_text,
    }
    return {
        "ok": all(checks.values()),
        "version": VERSION,
        "pyproject_version": pyproject_version,
        "checks": checks,
        "graph_counts": {
            "languages": graph_counts.get("languages", 0),
            "phrase_translations": graph_counts.get("phrase_translations", 0),
            "language_variants": graph_counts.get("language_variants", 0),
            "language_capabilities": graph_counts.get("language_capabilities", 0),
            "pronunciation_profiles": graph_counts.get("pronunciation_profiles", 0),
            "phonology_profiles": graph_counts.get("phonology_profiles", 0),
            "transliteration_profiles": graph_counts.get("transliteration_profiles", 0),
            "semantic_concepts": graph_counts.get("semantic_concepts", 0),
            "concept_links": graph_counts.get("concept_links", 0),
            "provider_registry": graph_counts.get("provider_registry", 0),
        },
    }
