from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_write_budget_denies_large_payload(tmp_path):
    kernel = KernelEngine(db_path=tmp_path / "events.sqlite")
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path / "ws")
    giant = "x" * 100_001
    result = runtime.handle(f"write file big.txt :: {giant}")
    assert result["status"] == "denied"
    assert "bytes" in result["reason"].lower() or "budget" in result["reason"].lower()


def test_execution_records_plan_and_evaluation(tmp_path):
    kernel = KernelEngine(db_path=tmp_path / "events.sqlite")
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path / "ws")
    result = runtime.handle("write file hello.txt :: hi there")
    assert result["status"] == "approve"
    state = kernel.state()
    assert state.plan_summaries
    assert state.evaluations
    assert result["evaluation"]["validator_pass_rate"] >= 0.5
