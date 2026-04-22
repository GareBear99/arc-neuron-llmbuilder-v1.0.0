from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime import LuciferRuntime
from dashboards.trace_viewer import render_trace


def main() -> None:
    workspace = Path(".runtime_workspace")
    kernel = KernelEngine(db_path=workspace / "runtime.db")
    runtime = LuciferRuntime(kernel=kernel, workspace_root=workspace)
    print(runtime.handle("write notes.txt :: hello from ARC Lucifer"))
    print(runtime.handle("read notes.txt"))
    print(runtime.handle("delete notes.txt"))
    print(runtime.handle("delete notes.txt", confirm=True))
    trace = render_trace(kernel, workspace / "trace.html")
    print({"trace": str(trace)})


if __name__ == "__main__":
    main()
