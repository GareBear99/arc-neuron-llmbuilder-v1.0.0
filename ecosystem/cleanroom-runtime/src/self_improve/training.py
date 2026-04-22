from __future__ import annotations

"""Training/export helpers for future custom GGUF-oriented model work.

The runtime stays open-ended: these exports are plain JSONL so they can feed
custom trainers, fine-tune pipelines, or external tools without forcing one
backend or one model family.
"""

import json
from pathlib import Path
from typing import Any

from arc_kernel.state import ProjectedState


class TrainingCorpusExporter:
    def export_supervised(self, state: ProjectedState, output_path: str | Path) -> dict[str, Any]:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open('w', encoding='utf-8') as handle:
            for item in state.inputs:
                text = item.get('text') or item.get('model_prompt')
                if not text:
                    continue
                example = {
                    'kind': 'instruction',
                    'input': text,
                    'metadata': item,
                }
                handle.write(json.dumps(example, sort_keys=True) + '\n')
                count += 1
            for run in state.model_runs:
                example = {
                    'kind': 'model_run',
                    'input': run.get('prompt') or run.get('input') or '',
                    'output': run.get('completion_text') or run.get('text') or '',
                    'exact_prompt_tokens': run.get('exact_prompt_tokens'),
                    'exact_completion_tokens': run.get('exact_completion_tokens'),
                    'backend': run.get('backend'),
                    'status': run.get('kind'),
                }
                handle.write(json.dumps(example, sort_keys=True) + '\n')
                count += 1
            for receipt in state.receipts:
                outputs = receipt.get('outputs', {})
                example = {
                    'kind': 'receipt',
                    'proposal_id': receipt.get('proposal_id'),
                    'success': receipt.get('success'),
                    'outputs': outputs,
                    'validator_results': receipt.get('validator_results', []),
                }
                handle.write(json.dumps(example, sort_keys=True) + '\n')
                count += 1
        return {'status': 'ok', 'output_path': str(path.resolve()), 'examples_written': count, 'corpus_type': 'supervised_jsonl'}

    def export_preferences(self, state: ProjectedState, output_path: str | Path) -> dict[str, Any]:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open('w', encoding='utf-8') as handle:
            for run in state.improvement_runs:
                if run.get('kind') not in {'candidate_scores', 'candidate_best'}:
                    continue
                candidates = run.get('candidates') or []
                best = run.get('best_candidate')
                if not candidates or not best:
                    continue
                for candidate in candidates:
                    if candidate.get('candidate_id') == best.get('candidate_id'):
                        continue
                    example = {
                        'kind': 'preference_pair',
                        'run_id': run.get('run_id'),
                        'preferred': best,
                        'rejected': candidate,
                    }
                    handle.write(json.dumps(example, sort_keys=True) + '\n')
                    count += 1
        return {'status': 'ok', 'output_path': str(path.resolve()), 'examples_written': count, 'corpus_type': 'preference_jsonl'}
