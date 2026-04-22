from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_shell_budget_caps_usage(tmp_path):
    kernel = KernelEngine(db_path=tmp_path / "events.sqlite")
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path / "ws")
    for _ in range(10):
        out = runtime.handle("shell echo hi")
        assert out["status"] == "approve"
    denied = runtime.handle("shell echo over")
    assert denied["status"] == "denied"
    assert "budget" in denied["reason"].lower()
