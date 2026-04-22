from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ImprovementTarget:
    key: str
    priority: str
    title: str
    rationale: str
    action_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'priority': self.priority,
            'title': self.title,
            'rationale': self.rationale,
            'action_hint': self.action_hint,
        }


class ImprovementAnalyzer:
    def analyze(self, state: Any, workspace_root: str | Path) -> dict[str, Any]:
        targets: list[ImprovementTarget] = []
        world = getattr(state, 'world_model', {}) or {}
        benchmark_runs = getattr(state, 'benchmark_runs', []) or []
        model_runs = getattr(state, 'model_runs', []) or []
        pending = getattr(state, 'pending_confirmations', []) or []
        denied = getattr(state, 'denied_proposals', []) or []
        receipts = getattr(state, 'receipts', []) or []
        known_files = world.get('known_files', []) or []
        mirrored_headers = world.get('mirrored_memory_headers', []) or []
        top_memory_keywords = world.get('top_memory_keywords', []) or []
        fallback_events = getattr(state, 'fallback_events', []) or []
        workspace = Path(workspace_root)
        trace_path = workspace / 'trace.html'

        if not benchmark_runs:
            targets.append(ImprovementTarget(
                key='benchmarks_missing',
                priority='high',
                title='Run baseline benchmark suite',
                rationale='No benchmark runs are recorded yet, so the system cannot measure regressions or improvements.',
                action_hint='Run `lucifer bench` and store the result before changing planner or model behavior.',
            ))
        else:
            latest = benchmark_runs[-1]
            pass_rate = float(latest.get('pass_rate', 0.0))
            if pass_rate < 1.0:
                targets.append(ImprovementTarget(
                    key='benchmark_failures',
                    priority='high',
                    title='Investigate failing benchmarks',
                    rationale=f'Latest benchmark pass rate is {pass_rate:.2f}, indicating regressions or incomplete behaviors.',
                    action_hint='Inspect the latest benchmark payload in state and prioritize failing benchmark cases first.',
                ))

        if not model_runs:
            targets.append(ImprovementTarget(
                key='model_path_unvalidated',
                priority='medium',
                title='Validate local model prompt path',
                rationale='No model prompt runs are recorded yet, so the managed llamafile path is not validated in this workspace.',
                action_hint='Run `lucifer prompt ... --stream` with your local llamafile binary and GGUF model.',
            ))

        if pending:
            targets.append(ImprovementTarget(
                key='pending_proposals',
                priority='medium',
                title='Resolve pending confirmations',
                rationale=f'{len(pending)} proposal(s) are waiting for operator confirmation and may block follow-up work.',
                action_hint='Use `lucifer approve <proposal_id>` or `lucifer reject <proposal_id>` for each pending proposal.',
            ))

        if denied:
            targets.append(ImprovementTarget(
                key='denied_proposals',
                priority='medium',
                title='Review denied proposal patterns',
                rationale=f'{len(denied)} proposal(s) were denied; this often points to policy friction or risky default behavior.',
                action_hint='Inspect denied proposals in `lucifer state` and tighten routing or policy configuration where appropriate.',
            ))

        if receipts and not trace_path.exists():
            targets.append(ImprovementTarget(
                key='trace_missing',
                priority='low',
                title='Generate an operator trace snapshot',
                rationale='Receipts exist but no trace snapshot is present in the workspace.',
                action_hint='Run `lucifer trace --output trace.html` to create a human-readable audit surface.',
            ))

        if known_files and len(known_files) > 20:
            targets.append(ImprovementTarget(
                key='workspace_growth',
                priority='low',
                title='Promote hot workspace knowledge into retained memory',
                rationale=f'The world model is tracking {len(known_files)} known files; retention and compaction should be exercised regularly.',
                action_hint='Run `lucifer compact` and validate the memory retention schedule before the hot set grows further.',
            ))

        if mirrored_headers and not top_memory_keywords:
            targets.append(ImprovementTarget(
                key='memory_metadata_refresh',
                priority='medium',
                title='Refresh mirrored memory headers for retrieval quality',
                rationale='Mirrored memory exists but does not expose strong keyword clustering yet, which weakens planning and retrieval.',
                action_hint='Review title/summary/keywords for mirrored memories and run `lucifer memory sync` so archive mirrors stay aligned.',
            ))

        if top_memory_keywords:
            keyword_label = ', '.join(item.get('keyword', '') for item in top_memory_keywords[:3] if item.get('keyword'))
            targets.append(ImprovementTarget(
                key='memory_guided_planning',
                priority='low',
                title='Use mirrored memory themes in improvement planning',
                rationale=f'Mirrored memory is surfacing recurring themes ({keyword_label}); improvement runs should keep those priorities visible.',
                action_hint='Run `lucifer memory search "' + keyword_label.split(', ')[0] + '"` and fold the strongest mirrored memories into the next self-improvement plan.',
            ))

        if fallback_events and len(fallback_events) >= 3:
            targets.append(ImprovementTarget(
                key='fallback_hotspots',
                priority='medium',
                title='Reduce repeated fallback usage',
                rationale=f'{len(fallback_events)} fallback event(s) are recorded, indicating recurring instability in preferred execution paths.',
                action_hint='Inspect `lucifer failures` and prioritize fixes for the most common degraded execution modes.',
            ))

        if not targets:
            targets.append(ImprovementTarget(
                key='stable_baseline',
                priority='low',
                title='Maintain baseline and proceed to soak testing',
                rationale='No urgent repo-side gaps were detected from the current state snapshot.',
                action_hint='Continue with real-device soak testing, model validation, and workload-specific benchmark expansion.',
            ))

        priority_weight = {'high': 3, 'medium': 2, 'low': 1}
        targets.sort(key=lambda t: (-priority_weight.get(t.priority, 0), t.key))
        return {
            'status': 'ok',
            'summary': {
                'target_count': len(targets),
                'proposal_count': len(getattr(state, 'proposals', []) or []),
                'receipt_count': len(receipts),
                'model_run_count': len(model_runs),
                'benchmark_count': len(benchmark_runs),
                'fallback_count': len(fallback_events),
                'mirrored_memory_count': len(mirrored_headers),
            },
            'targets': [t.to_dict() for t in targets],
        }
