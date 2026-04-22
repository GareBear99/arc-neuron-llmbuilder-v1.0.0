from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from arc_kernel.engine import KernelEngine


@dataclass
class BenchmarkResult:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {'name': self.name, 'passed': self.passed, 'detail': self.detail}


class BenchmarkRunner:
    def run_smoke_suite(self, workspace_root: str | Path) -> dict[str, Any]:
        from lucifer_runtime.runtime import LuciferRuntime

        with TemporaryDirectory(prefix='arc_bench_') as tmpdir:
            db_path = Path(tmpdir) / 'bench.sqlite3'
            runtime = LuciferRuntime(kernel=KernelEngine(db_path=db_path), workspace_root=workspace_root)
            results: list[BenchmarkResult] = []
            write_res = runtime.handle('write bench_smoke.txt :: benchmark payload')
            results.append(BenchmarkResult('write_file', bool(write_res.get('result', {}).get('written')), 'write command should succeed'))
            read_res = runtime.handle('read bench_smoke.txt')
            results.append(BenchmarkResult('read_file', read_res.get('result', {}).get('content') == 'benchmark payload', 'read should return written content'))
            state = runtime.kernel.state()
            results.append(BenchmarkResult('state_persistence', len(state.receipts) >= 2, 'runtime should record receipts during benchmark'))
            runtime.kernel.close()
        passed = sum(1 for r in results if r.passed)
        return {
            'kind': 'benchmark_run',
            'suite': 'smoke',
            'results': [r.to_dict() for r in results],
            'passed': passed,
            'total': len(results),
            'pass_rate': round(passed / len(results), 3) if results else 0.0,
        }
