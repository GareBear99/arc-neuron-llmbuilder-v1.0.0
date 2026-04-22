from __future__ import annotations
import json
from arc.core.db import connect
from arc.core.schemas import ProposalIn, ProposalOut, new_id, utcnow
from arc.core.simulator import simulate


def create_proposal(prop: ProposalIn, created_by_role: str, risk_score: float) -> ProposalOut:
    proposal_id = new_id("prop")
    sim = simulate(prop.action, prop.target_id, risk_score, depth=prop.simulation_depth)
    with connect() as conn:
        conn.execute(
            "INSERT INTO proposals (proposal_id, created_at, status, created_by_role, action, target_type, target_id, rationale, simulation_json, approved_at) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, NULL)",
            (proposal_id, utcnow(), created_by_role, prop.action, prop.target_type, prop.target_id, prop.rationale, json.dumps(sim, sort_keys=True)),
        )
        conn.commit()
    return get_proposal(proposal_id)


def get_proposal(proposal_id: str) -> ProposalOut:
    with connect() as conn:
        row = conn.execute("SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
        if not row:
            raise KeyError(proposal_id)
        return ProposalOut(
            proposal_id=row["proposal_id"],
            created_at=row["created_at"],
            status=row["status"],
            created_by_role=row["created_by_role"],
            action=row["action"],
            target_type=row["target_type"],
            target_id=row["target_id"],
            rationale=row["rationale"],
            simulation=json.loads(row["simulation_json"]),
            approved_at=row["approved_at"],
        )


def approve_proposal(proposal_id: str) -> ProposalOut:
    with connect() as conn:
        row = conn.execute("SELECT status FROM proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
        if not row:
            raise KeyError(proposal_id)
        if row["status"] != "approved":
            conn.execute("UPDATE proposals SET status = 'approved', approved_at = ? WHERE proposal_id = ?", (utcnow(), proposal_id))
            conn.commit()
    return get_proposal(proposal_id)


def list_proposals() -> list[dict]:
    with connect() as conn:
        return [{**dict(r), "simulation": json.loads(r["simulation_json"])} for r in conn.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()]
