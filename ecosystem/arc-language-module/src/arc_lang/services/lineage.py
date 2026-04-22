from __future__ import annotations
from arc_lang.core.db import connect
from arc_lang.services.manual_lineage import list_custom_lineage
from arc_lang.services.arbitration import resolve_effective_lineage


def _walk_node_chain(conn, node_id: str | None) -> list[dict]:
    chain: list[dict] = []
    seen: set[str] = set()
    current = node_id
    while current and current not in seen:
        seen.add(current)
        row = conn.execute(
            'SELECT node_id, node_type, name, parent_node_id FROM lineage_nodes WHERE node_id = ?',
            (current,),
        ).fetchone()
        if not row:
            break
        chain.append(dict(row))
        current = row['parent_node_id']
    return chain


def get_lineage(language_id: str) -> dict:
    """Return the full lineage graph (nodes and edges) for a language."""
    with connect() as conn:
        lang = conn.execute(
            "SELECT language_id, name, family, branch, parent_language_id, family_node_id, branch_node_id FROM languages WHERE language_id = ?",
            (language_id,),
        ).fetchone()
        if not lang:
            return {"ok": False, "error": "language_not_found", "language_id": language_id}
        edges = [dict(r) for r in conn.execute(
            "SELECT src_id, dst_id, relation, confidence, disputed, source_ref FROM lineage_edges WHERE src_id = ? ORDER BY relation",
            (language_id,),
        ).fetchall()]
        prov = [dict(r) for r in conn.execute(
            "SELECT source_name, source_ref, confidence, notes FROM provenance_records WHERE record_type = 'language' AND record_id = ? ORDER BY confidence DESC",
            (language_id,),
        ).fetchall()]
        node_chain = _walk_node_chain(conn, lang['branch_node_id'] or lang['family_node_id'])
        node_provenance = {}
        for node in node_chain:
            node_provenance[node['node_id']] = [dict(r) for r in conn.execute(
                "SELECT source_name, source_ref, confidence, notes FROM provenance_records WHERE record_type = 'lineage_node' AND record_id = ? ORDER BY confidence DESC",
                (node['node_id'],),
            ).fetchall()]

    path = [{"kind": node['node_type'], "value": node['name'], "node_id": node['node_id']} for node in node_chain]
    custom = list_custom_lineage(src_id=language_id)['results']
    custom += [r for r in list_custom_lineage(dst_id=language_id)['results'] if r not in custom]
    effective = resolve_effective_lineage(language_id)
    return {
        "ok": True,
        "language": dict(lang),
        "path": path,
        "edges": edges,
        "lineage_nodes": node_chain,
        "lineage_node_provenance": node_provenance,
        "provenance": prov,
        "custom_assertions": custom,
        "effective_truth": effective.get('effective_truth', {}),
        "conflicts": effective.get('conflicts', []),
    }
