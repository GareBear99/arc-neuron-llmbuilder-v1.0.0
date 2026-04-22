from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_write_and_read_file_roundtrip(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    write_result = runtime.handle("write notes.txt :: hello world")
    assert write_result["status"] == "approve"
    read_result = runtime.handle("read notes.txt")
    assert read_result["result"]["content"] == "hello world"


def test_allowlisted_shell_command_runs(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    result = runtime.handle("shell pwd")
    assert result["status"] == "approve"
    assert "stdout" in result["result"]
