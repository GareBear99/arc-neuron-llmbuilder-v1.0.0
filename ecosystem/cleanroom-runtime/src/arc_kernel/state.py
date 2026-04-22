"""State projection builds a query-friendly runtime view from the append-only event log."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .schemas import EventKind


@dataclass
class ProjectedState:
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    proposals: List[Dict[str, Any]] = field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = field(default_factory=list)
    executions: List[Dict[str, Any]] = field(default_factory=list)
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    branch_plans: List[Dict[str, Any]] = field(default_factory=list)
    branch_scores: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    plan_summaries: List[Dict[str, Any]] = field(default_factory=list)
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = field(default_factory=list)
    archive_manifests: List[Dict[str, Any]] = field(default_factory=list)
    model_runs: List[Dict[str, Any]] = field(default_factory=list)
    benchmark_runs: List[Dict[str, Any]] = field(default_factory=list)
    world_model: Dict[str, Any] = field(default_factory=dict)
    improvement_runs: List[Dict[str, Any]] = field(default_factory=list)
    code_edits: List[Dict[str, Any]] = field(default_factory=list)
    fallback_events: List[Dict[str, Any]] = field(default_factory=list)
    fixnet_cases: List[Dict[str, Any]] = field(default_factory=list)
    fixnet_archives: List[Dict[str, Any]] = field(default_factory=list)
    trust_profiles: List[Dict[str, Any]] = field(default_factory=list)
    curriculum_updates: List[Dict[str, Any]] = field(default_factory=list)
    directives: List[Dict[str, Any]] = field(default_factory=list)
    continuity_events: List[Dict[str, Any]] = field(default_factory=list)
    pending_confirmations: List[str] = field(default_factory=list)
    completed_proposals: List[str] = field(default_factory=list)
    denied_proposals: List[str] = field(default_factory=list)


class StateProjector:
    def project(self, events):
        state = ProjectedState()
        latest_decisions: Dict[str, str] = {}
        receipts_by_proposal: set[str] = set()
        known_files: Dict[str, Dict[str, Any]] = {}
        recent_outputs: List[Dict[str, Any]] = []
        model_runs_by_id: Dict[str, Dict[str, Any]] = {}
        for event in events:
            if event.kind == EventKind.INPUT:
                state.inputs.append(event.payload)
            elif event.kind == EventKind.PROPOSAL:
                state.proposals.append(event.payload)
            elif event.kind == EventKind.POLICY_DECISION:
                state.policy_decisions.append(event.payload)
                latest_decisions[event.payload['proposal_id']] = event.payload['decision']
            elif event.kind == EventKind.EXECUTION:
                state.executions.append(event.payload)
            elif event.kind == EventKind.RECEIPT:
                state.receipts.append(event.payload)
                receipts_by_proposal.add(event.payload['proposal_id'])
                outputs = event.payload.get('outputs', {})
                path = outputs.get('path')
                if path:
                    known_files[str(path)] = {
                        'path': str(path),
                        'last_success': bool(event.payload.get('success')),
                        'content_preview': str(outputs.get('content', ''))[:120],
                        'bytes': outputs.get('bytes'),
                        'receipt_id': event.payload.get('receipt_id'),
                    }
                    recent_outputs.append({'path': str(path), 'outputs': outputs, 'success': bool(event.payload.get('success'))})
            elif event.kind == EventKind.BRANCH_PLAN:
                state.branch_plans.append(event.payload)
                proposal_id = event.payload.get('proposal_id')
                if proposal_id:
                    state.branch_scores[proposal_id] = list(event.payload.get('candidates', []))
            elif event.kind == EventKind.EVALUATION:
                state.evaluations.append(event.payload)
                kind = event.payload.get('kind')
                if kind == 'plan_summary':
                    state.plan_summaries.append(event.payload)
                elif kind in {'model_prompt_complete', 'model_prompt_interrupted'}:
                    run_id = event.payload.get('run_id') or f"{kind}:{len(state.model_runs)}"
                    model_runs_by_id[run_id] = dict(event.payload)
                elif kind == 'benchmark_run':
                    state.benchmark_runs.append(event.payload)
                elif kind in {'self_improve_plan', 'self_improve_run', 'self_improve_validation', 'self_improve_promotion', 'self_improve_patch', 'self_improve_cycle', 'self_improve_fault', 'self_improve_adversarial_cycle'}:
                    state.improvement_runs.append(event.payload)
                elif kind in {'code_index', 'code_plan', 'code_verify', 'code_patch'}:
                    state.code_edits.append(event.payload)
                elif kind == 'fallback_event':
                    state.fallback_events.append(event.payload)
                elif kind in {'fixnet_case','fixnet_fix'}:
                    state.fixnet_cases.append(event.payload)
                elif kind == 'fixnet_embedded_archive':
                    state.fixnet_archives.append(event.payload)
                elif kind == 'tool_trust':
                    state.trust_profiles.append(event.payload)
                elif kind == 'curriculum_memory':
                    state.curriculum_updates.append(event.payload)
                elif kind == 'directive_ledger':
                    state.directives.append(event.payload)
                elif kind in {'continuity_boot', 'continuity_heartbeat'}:
                    state.continuity_events.append(event.payload)
            elif event.kind == EventKind.MEMORY_UPDATE:
                state.memory_updates.append(event.payload)
                if event.payload.get('kind') == 'archive_created':
                    state.archive_manifests.append(event.payload)
        all_proposals = [proposal['proposal_id'] for proposal in state.proposals]
        for proposal_id in all_proposals:
            if proposal_id in receipts_by_proposal:
                state.completed_proposals.append(proposal_id)
                continue
            decision = latest_decisions.get(proposal_id)
            if decision == 'require_confirmation':
                state.pending_confirmations.append(proposal_id)
            elif decision == 'deny':
                state.denied_proposals.append(proposal_id)
        state.model_runs = list(model_runs_by_id.values())
        mirrored_live_count = sum(1 for update in state.memory_updates if update.get('kind') == 'archive_mirrored')
        retired_count = sum(1 for update in state.memory_updates if update.get('kind') == 'archive_retired')
        mirrored_headers = []
        keyword_weights: dict[str, int] = {}
        for update in state.memory_updates:
            kind = update.get('kind')
            if kind == 'archive_mirrored':
                mirrored_headers.append({
                    'target_event_id': update.get('target_event_id'),
                    'title': update.get('title'),
                    'summary': update.get('summary'),
                    'keywords': update.get('keywords', []),
                    'archive_branch_id': update.get('archive_branch_id'),
                    'status': 'live_and_archived',
                })
                for keyword in update.get('keywords', []) or []:
                    key = str(keyword)
                    keyword_weights[key] = keyword_weights.get(key, 0) + 1
        top_memory_keywords = [
            {'keyword': keyword, 'count': count}
            for keyword, count in sorted(keyword_weights.items(), key=lambda item: (-item[1], item[0]))[:10]
        ]
        state.world_model = {
            'known_files': sorted(known_files.values(), key=lambda item: item['path']),
            'recent_outputs': recent_outputs[-10:],
            'proposal_count': len(state.proposals),
            'receipt_count': len(state.receipts),
            'model_run_count': len(state.model_runs),
            'benchmark_count': len(state.benchmark_runs),
            'improvement_run_count': len(state.improvement_runs),
            'adversarial_event_count': sum(1 for item in state.improvement_runs if item.get('kind') in {'self_improve_fault', 'self_improve_adversarial_cycle'}),
            'code_edit_count': len(state.code_edits),
            'fallback_count': len(state.fallback_events),
            'mirrored_live_memory_count': mirrored_live_count,
            'retired_memory_count': retired_count,
            'mirrored_memory_headers': mirrored_headers[-20:],
            'top_memory_keywords': top_memory_keywords,
            'fixnet_case_count': len(state.fixnet_cases),
            'fixnet_archive_count': len(state.fixnet_archives),
            'recent_fixnet_cases': state.fixnet_cases[-10:],
            'recent_fixnet_archives': state.fixnet_archives[-10:],
            'tool_trust_profile_count': len(state.trust_profiles),
            'recent_tool_trust_profiles': state.trust_profiles[-10:],
            'curriculum_update_count': len(state.curriculum_updates),
            'recent_curriculum_updates': state.curriculum_updates[-10:],
            'directive_count': len(state.directives),
            'active_directive_count': sum(1 for item in state.directives if item.get('status') == 'active'),
            'recent_directives': state.directives[-10:],
            'continuity_event_count': len(state.continuity_events),
            'recent_continuity_events': state.continuity_events[-10:],
        }
        return state
