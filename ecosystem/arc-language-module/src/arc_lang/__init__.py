"""
ARC Language Module — governed multilingual language/script/lineage substrate.

Quick-start::

    from arc_lang.core.db import init_db
    from arc_lang.services.seed_ingest import ingest_common_seed
    from arc_lang.services.stats import get_graph_stats

    init_db()
    ingest_common_seed()
    print(get_graph_stats())

CLI entry-point::

    python -m arc_lang.cli.main --help

API (requires uvicorn)::

    uvicorn arc_lang.api.app:app --reload
"""
from arc_lang.version import VERSION

__version__ = VERSION
__author__ = "ARC System"

# Convenience re-exports for common entry points
from arc_lang.core.db import init_db, connect          # noqa: F401
from arc_lang.services.seed_ingest import ingest_common_seed  # noqa: F401
from arc_lang.services.stats import get_graph_stats    # noqa: F401
