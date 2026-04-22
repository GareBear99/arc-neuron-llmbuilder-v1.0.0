from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from arc_kernel.engine import KernelEngine
from arc_kernel.schemas import Proposal, Capability, RiskLevel, Receipt
from memory_subsystem import MemoryManager, RetentionConfig


def main() -> None:
    root = Path(".demo_memory")
    kernel = KernelEngine(db_path=root / "events.db")

    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=240)).isoformat()
    input_event = kernel.record_input("user", {"text": "inspect archive behavior"})
    input_event.created_at = old_timestamp
    proposal = Proposal(
        action="read_file",
        capability=Capability(name="file.read", description="Read a file", risk=RiskLevel.LOW),
        params={"path": "notes.txt"},
        proposed_by="lucifer",
        rationale="demo",
        created_at=old_timestamp,
    )
    kernel.record_proposal("lucifer", proposal, parent_event_id=input_event.event_id)
    kernel.record_receipt("lucifer", Receipt(proposal_id=proposal.proposal_id, success=True, outputs={"text": "ok"}, validator_results=[]))

    manager = MemoryManager(kernel, root / "memory", RetentionConfig(hot_days=30, warm_days=180))
    result = manager.consolidate()
    print({
        "hot_count": result.hot_count,
        "warm_count": result.warm_count,
        "archived_count": result.archived_count,
        "archives": [pack.archive_path.name for pack in manager.list_archives()],
    })


if __name__ == "__main__":
    main()
