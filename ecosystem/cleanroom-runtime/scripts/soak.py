from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def run_soak(workspace: Path, iterations: int, sleep_seconds: float) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    db_path = workspace / '.arc_lucifer' / 'soak.sqlite3'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    kernel = KernelEngine(db_path=db_path)
    runtime = LuciferRuntime(kernel=kernel, workspace_root=workspace)
    receipts = []
    started = time.time()
    for index in range(iterations):
        text = f'soak iteration {index + 1}'
        write_result = runtime.handle(f'write soak_{index + 1}.txt {text}', confirm=True)
        state_result = runtime.kernel.state()
        receipts.append({
            'iteration': index + 1,
            'write_status': write_result.get('status'),
            'proposal_id': write_result.get('proposal_id'),
            'events': len(state_result.receipts),
            'pending': len(state_result.pending_confirmations),
        })
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    duration = time.time() - started
    stats = runtime.kernel.stats()
    return {
        'status': 'ok',
        'iterations': iterations,
        'sleep_seconds': sleep_seconds,
        'duration_seconds': round(duration, 3),
        'workspace': str(workspace),
        'db_path': str(db_path),
        'stats': stats,
        'receipts': receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Deterministic local soak harness for ARC Lucifer runtime.')
    parser.add_argument('--workspace', default='.', help='Workspace used for the soak run.')
    parser.add_argument('--iterations', type=int, default=5)
    parser.add_argument('--sleep-seconds', type=float, default=0.0)
    parser.add_argument('--output', default=None, help='Optional JSON path for the soak receipt.')
    args = parser.parse_args()

    result = run_soak(Path(args.workspace).expanduser().resolve(), iterations=args.iterations, sleep_seconds=args.sleep_seconds)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + '\n', encoding='utf-8')
    print(payload)
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
