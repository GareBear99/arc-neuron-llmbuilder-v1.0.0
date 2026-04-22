from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from arc_kernel.engine import KernelEngine
from arc_kernel.schemas import Capability, Proposal, Receipt, RiskLevel
from memory_subsystem import MemoryManager, RetentionConfig


def _proposal(created_at: str, path: str = "old.txt") -> Proposal:
    return Proposal(
        action="read_file",
        capability=Capability(name="file.read", description="Read file", risk=RiskLevel.LOW),
        params={"path": path},
        proposed_by="lucifer",
        rationale="test",
        created_at=created_at,
    )


def test_old_records_archive_into_arcpack(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / "events.db")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=240)).isoformat()
    input_event = kernel.record_input("user", {"text": "old prompt"})
    input_event.created_at = old_timestamp
    proposal = _proposal(old_timestamp)
    kernel.record_proposal("lucifer", proposal, parent_event_id=input_event.event_id)
    kernel.record_receipt("lucifer", Receipt(proposal_id=proposal.proposal_id, success=True, outputs={"ok": True}, validator_results=[]))
    kernel.log._events[-1].created_at = old_timestamp

    manager = MemoryManager(kernel, tmp_path / "memory", RetentionConfig(hot_days=30, warm_days=180))
    result = manager.consolidate(now=datetime.now(timezone.utc))

    assert result.archived_count >= 2
    archives = manager.list_archives()
    assert len(archives) == 1
    assert archives[0].manifest["record_count"] == result.archived_count
    assert kernel.state().archive_manifests


def test_recently_accessed_record_stays_warm(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / "events.db")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=240)).isoformat()
    recent_access = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    event = kernel.record_input("user", {"text": "keep warm", "last_accessed_at": recent_access})
    event.created_at = old_timestamp

    manager = MemoryManager(kernel, tmp_path / "memory", RetentionConfig(hot_days=30, warm_days=180, access_grace_days=45))
    result = manager.consolidate(now=datetime.now(timezone.utc))

    assert result.archived_count == 0
    warm_index = (tmp_path / "memory" / "warm" / "warm_index.json").read_text(encoding="utf-8")
    assert "keep warm" in warm_index


def test_pinned_record_never_archives(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / "events.db")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    event = kernel.record_input("user", {"text": "pin me", "memory_pinned": True})
    event.created_at = old_timestamp

    manager = MemoryManager(kernel, tmp_path / "memory", RetentionConfig())
    result = manager.consolidate(now=datetime.now(timezone.utc))

    assert result.archived_count == 0
    assert manager.list_archives() == []
