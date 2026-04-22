from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_state_tracks_pending_confirmation(tmp_path: Path):
    target = tmp_path / "temp.log"
    target.write_text("bye", encoding="utf-8")
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    result = runtime.handle("delete temp.log")
    state = runtime.kernel.state()
    assert result["proposal_id"] in state.pending_confirmations


def test_state_can_be_replayed_to_receipt(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    write = runtime.handle("write notes.txt :: hello world")
    replay_state = runtime.replay_state_at_receipt(write["proposal_id"])
    assert replay_state is not None
    assert len(replay_state.receipts) >= 1
