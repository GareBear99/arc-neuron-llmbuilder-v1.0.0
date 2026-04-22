from pathlib import Path

from lucifer_runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine


def test_low_risk_flow_records_receipt(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    result = runtime.handle("list the current files")
    assert result["status"] == "approve"
    state = runtime.kernel.state()
    assert len(state.receipts) == 1
    assert len(state.branch_plans) == 1


def test_high_risk_flow_requires_confirmation_then_executes(tmp_path: Path):
    target = tmp_path / "temp.log"
    target.write_text("bye", encoding="utf-8")
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    result = runtime.handle("delete temp.log")
    assert result["status"] == "require_confirmation"
    assert target.exists()
    confirmed = runtime.handle("delete temp.log", confirm=True)
    assert confirmed["status"] == "confirmed"
    assert not target.exists()
