from pathlib import Path

from arc_kernel.engine import KernelEngine
from dashboards.trace_viewer import render_trace
from lucifer_runtime.runtime import LuciferRuntime


def test_sqlite_persistence_reloads_events(tmp_path: Path):
    db_path = tmp_path / "events.db"
    runtime = LuciferRuntime(KernelEngine(db_path=db_path), workspace_root=tmp_path)
    runtime.handle("list the current files")
    runtime.kernel.close()

    reloaded = KernelEngine(db_path=db_path)
    state = reloaded.state()
    assert len(state.inputs) >= 1
    assert len(state.receipts) >= 1


def test_trace_viewer_renders_html(tmp_path: Path):
    kernel = KernelEngine(db_path=tmp_path / "events.db")
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path)
    runtime.handle("list the current files")
    trace_path = render_trace(kernel, tmp_path / "trace.html")
    assert trace_path.exists()
    assert "ARC Lucifer Trace Viewer" in trace_path.read_text(encoding="utf-8")
