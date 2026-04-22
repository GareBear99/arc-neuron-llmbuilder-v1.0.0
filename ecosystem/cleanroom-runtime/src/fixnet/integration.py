from __future__ import annotations

from typing import Any, Optional

from .ledger import FixLedger
from .consensus import FixConsensus
from .novelty import FixNoveltyFilter
from .archive import EmbeddedFixArchive
from .models import FixRecord, RelationshipType


class FixNet:
    """DARPA-grade FixNet integration for ARC Lucifer runtime.

    This is the ARC-side mirror of LuciferAI FixNet architecture:
      - FixLedger (storage)
      - FixConsensus (analytics)
      - FixNoveltyFilter (novelty)
      - FixPublisher (optional... stub)
      - EmbeddedFixArchive (archive mirror)

    The runtime should record only references + small summaries into the ARC event spine,
    while FixNet stores the detailed fix objects.
    """

    def __init__(self, runtime_root: str) -> None:
        self.ledger = FixLedger(runtime_root)
        self.consensus = FixConsensus(runtime_root)
        self.novelty = FixNoveltyFilter(self.ledger)
        self.archive = EmbeddedFixArchive(runtime_root)

    def register_fix(
        self,
        *,
        title: str,
        error_type: str,
        error_signature: str,
        solution: str,
        summary: str = '',
        keywords: list[str] | None = None,
        context: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        linked_event_ids: list[str] | None = None,
        linked_run_ids: list[str] | None = None,
        linked_proposal_ids: list[str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        record = FixRecord(
            title=title,
            error_type=error_type,
            error_signature=error_signature,
            solution=solution,
            summary=summary,
            keywords=list(keywords or []),
            context=dict(context or {}),
            evidence=dict(evidence or {}),
            linked_event_ids=list(linked_event_ids or []),
            linked_run_ids=list(linked_run_ids or []),
            linked_proposal_ids=list(linked_proposal_ids or []),
        )
        record = self.ledger.upsert_fix(record)
        novelty = self.novelty.decide(
            fix_id=record.fix_id,
            error_signature=record.error_signature,
            error_type=record.error_type,
            solution=record.solution,
        )
        # if duplicate, create an edge to the original for audit, but keep record for traceability
        if novelty.decision == 'duplicate' and novelty.duplicate_of:
            self.ledger.add_edge(novelty.duplicate_of, record.fix_id, 'alternative_approach')
        elif novelty.decision == 'variant' and novelty.variant_of:
            self.ledger.add_edge(novelty.variant_of, record.fix_id, 'improved_version')
        return record.to_dict(), novelty.to_dict()

    def link(self, *, parent_fix_id: str, child_fix_id: str, relationship: RelationshipType) -> dict[str, Any]:
        edge = self.ledger.add_edge(parent_fix_id, child_fix_id, relationship)
        return edge.to_dict()

    def record_outcome(self, fix_id: str, *, succeeded: bool) -> dict[str, Any]:
        return self.consensus.record_outcome(fix_id, succeeded=succeeded).to_dict()

    def embed(self, fix_id: str, *, archive_branch_id: str = 'archive_branch_main') -> dict[str, Any]:
        fix = self.ledger.get_fix(fix_id)
        if not fix:
            raise ValueError(f'unknown fix_id: {fix_id}')
        consensus = self.consensus.get(fix_id)
        payload = {'fix': fix, 'consensus': consensus, 'edges': self.ledger.list_edges()}
        return self.archive.embed(fix_id=fix_id, payload=payload, archive_branch_id=archive_branch_id)

    def sync_archive(self, fix_id: str, *, status: str = 'live', retirement_at: str | None = None) -> dict[str, Any]:
        fix = self.ledger.get_fix(fix_id)
        if not fix:
            raise ValueError(f'unknown fix_id: {fix_id}')
        return self.archive.sync_metadata(fix_id, status=status, retirement_at=retirement_at, remote_ref=fix.get('remote_ref'))

    def retire_archive(self, fix_id: str, *, retirement_at: str | None = None) -> dict[str, Any]:
        return self.archive.retire(fix_id, retirement_at=retirement_at)

    def stats(self) -> dict[str, Any]:
        return {
            'fix_count': len(self.ledger.list_fixes()),
            'edge_count': len(self.ledger.list_edges()),
            'consensus': self.consensus.stats(),
            'embedded_archive_count': len(self.archive.index()),
            'embedded_archives': self.archive.index(),
        }
