from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_pending_proposal_can_be_approved_later(tmp_path: Path):
    target = tmp_path / "temp.log"
    target.write_text("bye", encoding="utf-8")
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    first = runtime.handle("delete temp.log")
    assert first["status"] == "require_confirmation"
    proposal_id = first["proposal_id"]
    later = runtime.approve(proposal_id)
    assert later["status"] == "confirmed"
    assert not target.exists()


def test_write_can_be_rolled_back(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    write = runtime.handle("write notes.txt :: hello world")
    proposal_id = write["proposal_id"]
    target = tmp_path / "notes.txt"
    assert target.read_text(encoding="utf-8") == "hello world"
    rolled = runtime.rollback(proposal_id)
    assert rolled["status"] == "rolled_back"
    assert not target.exists()
