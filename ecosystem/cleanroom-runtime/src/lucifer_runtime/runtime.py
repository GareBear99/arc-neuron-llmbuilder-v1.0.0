"""Primary runtime orchestration for deterministic tools, local model calls, and self-improvement flows."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from arc_kernel.engine import KernelEngine
from arc_kernel.schemas import Capability, Decision, EventKind, Proposal, Receipt, RiskLevel
from verifier.validators import validate_result
from cognition_services.planner import PlannerService
from cognition_services.evaluator import EvaluatorService
from cognition_services.goal_engine import GoalEngine
from cognition_services.shadow import ShadowExecutionService
from cognition_services.trust import ToolTrustRegistry
from cognition_services.directives import DirectiveLedger
from model_services import BackendRegistry, LlamafileBackend, LlamafileProcessManager
from self_improve import (
    BenchmarkRunner,
    ImprovementAnalyzer,
    ImprovementPlanner,
    SandboxManager,
    PromotionGate,
    ImprovementExecutor,
    CandidateCycleManager,
    AdversarialManager,
)
from code_editing import CodeEditPlanner, CodeVerifier, PatchEngine
from resilience import ContinuationManager, FailureClassifier, FallbackSelector, ContinuityShell
from .router import IntentRouter
from .tools import ToolRegistry
from .runtime_model import RuntimeModelMixin
from .runtime_code import RuntimeCodeMixin
from fixnet import FixNet
from memory_subsystem.curriculum import CurriculumMemory


class LuciferRuntime(RuntimeModelMixin, RuntimeCodeMixin):
    def __init__(
        self,
        kernel: KernelEngine | None = None,
        workspace_root: str | Path = '.',
        backend_registry: BackendRegistry | None = None,
    ) -> None:
        self.kernel = kernel or KernelEngine()
        self.workspace_root = Path(workspace_root)
        self.session_metrics = {
            'requests': 0,
            'prompt_chars': 0,
            'prompt_words': 0,
            'templated_prompt_chars': 0,
            'completion_chars': 0,
            'completion_words': 0,
            'exact_prompt_tokens': 0,
            'exact_completion_tokens': 0,
            'exact_total_tokens': 0,
        }
        self.router = IntentRouter()
        self.tools = ToolRegistry(workspace_root=workspace_root)
        self.planner = PlannerService()
        self.evaluator = EvaluatorService()
        self.goals = GoalEngine()
        self.directives = DirectiveLedger(workspace_root)
        self.shadow = ShadowExecutionService()
        self.trust = ToolTrustRegistry(workspace_root)
        self.curriculum = CurriculumMemory(workspace_root)
        self.benchmarks = BenchmarkRunner()
        self.improvement_analyzer = ImprovementAnalyzer()
        self.improvement_planner = ImprovementPlanner()
        self.sandbox_manager = SandboxManager()
        self.promotion_gate = PromotionGate()
        self.improvement_executor = ImprovementExecutor()
        self.candidate_cycles = CandidateCycleManager()
        self.adversarial = AdversarialManager()
        self.code_planner = CodeEditPlanner()
        self.code_verifier = CodeVerifier()
        self.patch_engine = PatchEngine()
        self.failure_classifier = FailureClassifier()
        self.fallback_selector = FallbackSelector()
        self.continuations = ContinuationManager()
        self.continuity = ContinuityShell(workspace_root, runtime_name='arc-lucifer-runtime')
        self.backends = backend_registry or BackendRegistry()
        self.fixnet = FixNet(str(self.workspace_root))
        if 'llamafile' not in self.backends.names():
            self.backends.register('llamafile', LlamafileBackend(process_manager=LlamafileProcessManager(keep_alive=True)))

    def register_directive(
        self,
        *,
        title: str,
        instruction: str,
        priority: int = 50,
        scope: str = 'global',
        constraints: list[str] | None = None,
        success_conditions: list[str] | None = None,
        abort_conditions: list[str] | None = None,
        persistence_mode: str = 'forever',
        issuer: str = 'operator',
        supersedes: str | None = None,
    ) -> dict:
        directive = self.directives.register(
            title=title,
            instruction=instruction,
            priority=priority,
            scope=scope,
            constraints=constraints,
            success_conditions=success_conditions,
            abort_conditions=abort_conditions,
            persistence_mode=persistence_mode,
            issuer=issuer,
            supersedes=supersedes,
        )
        payload = {'kind': 'directive_ledger', **directive}
        self.kernel.record_evaluation('directives', payload)
        return {'status': 'ok', 'directive': directive, **({'directive_id': directive.get('directive_id'), 'directive_status': directive.get('status')})}

    def complete_directive(self, directive_id: str, *, status: str = 'complete') -> dict:
        directive = self.directives.complete(directive_id, status=status)
        if directive is None:
            return {'status': 'error', 'reason': 'unknown_directive'}
        payload = {'kind': 'directive_ledger', **directive}
        self.kernel.record_evaluation('directives', payload)
        return {'status': 'ok', 'directive': directive, **({'directive_id': directive.get('directive_id'), 'directive_status': directive.get('status')})}

    def directive_stats(self) -> dict:
        return {'status': 'ok', **self.directives.stats()}

    def boot_continuity(self, *, fallback_available: bool = True, notes: str = '') -> dict:
        primary_available = 'llamafile' in self.backends.names()
        receipt = self.continuity.boot(
            active_directive_count=self.directives.stats().get('active_directive_count', 0),
            primary_available=primary_available,
            fallback_available=fallback_available,
            notes=notes,
        )
        payload = {'kind': 'continuity_boot', **receipt}
        self.kernel.record_evaluation('continuity', payload)
        return {'status': 'ok', 'boot_receipt': receipt, **({'mode': receipt.get('mode'), 'boot_index': receipt.get('boot_index')})}

    def continuity_heartbeat(self, *, mode: str | None = None, notes: str = '') -> dict:
        heartbeat = self.continuity.heartbeat(mode=mode, notes=notes)
        payload = {'kind': 'continuity_heartbeat', **heartbeat}
        self.kernel.record_evaluation('continuity', payload)
        return {'status': 'ok', 'heartbeat': heartbeat, **({'mode': heartbeat.get('mode'), 'heartbeat_at': heartbeat.get('heartbeat_at')})}

    def continuity_status(self) -> dict:
        watchdog = self.continuity.watchdog()
        return {'status': 'ok', **self.continuity.status(), 'watchdog': watchdog}

    def fixnet_register(
        self,
        *,
        title: str,
        error_type: str,
        error_signature: str,
        solution: str,
        summary: str = '',
        keywords: list[str] | None = None,
        context: dict | None = None,
        evidence: dict | None = None,
        linked_event_ids: list[str] | None = None,
        linked_run_ids: list[str] | None = None,
        linked_proposal_ids: list[str] | None = None,
        auto_embed: bool = False,
        archive_branch_id: str = 'archive_branch_main',
    ) -> dict:
        fix, novelty = self.fixnet.register_fix(
            title=title,
            error_type=error_type,
            error_signature=error_signature,
            solution=solution,
            summary=summary,
            keywords=keywords,
            context=context,
            evidence=evidence,
            linked_event_ids=linked_event_ids,
            linked_run_ids=linked_run_ids,
            linked_proposal_ids=linked_proposal_ids,
        )
        payload = {
            'kind': 'fixnet_fix',
            'fix_id': fix['fix_id'],
            'title': fix.get('title'),
            'error_type': fix.get('error_type'),
            'error_signature': fix.get('error_signature'),
            'summary': fix.get('summary'),
            'keywords': fix.get('keywords', []),
            'novelty': novelty,
        }
        self.kernel.record_evaluation('fixnet', payload)
        result = {'status': 'ok', 'fix': fix, 'novelty': novelty}
        if auto_embed:
            embedded = self.fixnet.embed(fix['fix_id'], archive_branch_id=archive_branch_id)
            embed_payload = {
                'kind': 'fixnet_embedded_archive',
                'fix_id': fix['fix_id'],
                'archive_branch_id': archive_branch_id,
                'archive_pack_id': embedded['archive_ref']['archive_pack_id'],
                'early_merge_at': embedded['archive_ref']['early_merge_at'],
                'last_sync_at': embedded['archive_ref']['last_sync_at'],
                'path': embedded['path'],
            }
            self.kernel.record_evaluation('fixnet', embed_payload)
            self.kernel.record_memory_update('fixnet', embed_payload)
            result['embedded'] = embedded
        return result

    def fixnet_embed(self, fix_id: str, *, archive_branch_id: str = 'archive_branch_main') -> dict:
        embedded = self.fixnet.embed(fix_id, archive_branch_id=archive_branch_id)
        embed_payload = {
            'kind': 'fixnet_embedded_archive',
            'fix_id': fix_id,
            'archive_branch_id': archive_branch_id,
            'archive_pack_id': embedded['archive_ref']['archive_pack_id'],
            'early_merge_at': embedded['archive_ref']['early_merge_at'],
            'last_sync_at': embedded['archive_ref']['last_sync_at'],
            'path': embedded['path'],
        }
        self.kernel.record_evaluation('fixnet', embed_payload)
        self.kernel.record_memory_update('fixnet', embed_payload)
        return {'status': 'ok', **embedded}

    def fixnet_stats(self) -> dict:
        return {'status': 'ok', **self.fixnet.stats()}

    def fixnet_sync_archive(self, fix_id: str, *, status: str = 'live', retirement_at: str | None = None) -> dict:
        synced = self.fixnet.sync_archive(fix_id, status=status, retirement_at=retirement_at)
        payload = {'kind': 'fixnet_embedded_archive', 'fix_id': fix_id, **synced}
        self.kernel.record_evaluation('fixnet', payload)
        self.kernel.record_memory_update('fixnet', payload)
        return {'status': 'ok', **synced}

    def record_tool_outcome(self, tool_name: str, *, succeeded: bool, notes: str = '', evidence: dict | None = None) -> dict:
        profile = self.trust.record_outcome(tool_name, succeeded=succeeded, notes=notes, evidence=evidence)
        payload = {'kind': 'tool_trust', **profile}
        self.kernel.record_evaluation('trust', payload)
        return {'status': 'ok', **profile}

    def tool_trust_stats(self) -> dict:
        return {'status': 'ok', **self.trust.stats()}

    def record_curriculum(self, *, theme: str, skill: str | None = None, failure_cluster: str | None = None, outcome: str = 'observed', notes: str = '') -> dict:
        data = self.curriculum.record(theme=theme, skill=skill, failure_cluster=failure_cluster, outcome=outcome, notes=notes)
        payload = {
            'kind': 'curriculum_memory',
            'theme': theme,
            'skill': skill,
            'failure_cluster': failure_cluster,
            'outcome': outcome,
            'notes': notes,
        }
        self.kernel.record_evaluation('curriculum', payload)
        return {'status': 'ok', **self.curriculum.stats()}

    def curriculum_stats(self) -> dict:
        return {'status': 'ok', **self.curriculum.stats()}

    def compile_goal(self, text: str, *, priority: int = 50) -> dict:
        goal = self.goals.compile_goal(text, priority=priority)
        payload = {'kind': 'goal_compilation', **goal.to_dict()}
        self.kernel.record_evaluation('goal-engine', payload)
        return {'status': 'ok', **goal.to_dict()}

    def shadow_handle(self, text: str, *, predicted_status: str = 'approve', confirm: bool = False) -> dict:
        predicted = {'status': predicted_status, 'text': text, 'branches': []}
        actual = self.handle(text, confirm=confirm)
        comparison = self.shadow.compare(predicted, actual).to_dict()
        payload = {'kind': 'shadow_execution', 'text': text, 'prediction': predicted, 'actual': actual, 'comparison': comparison}
        self.kernel.record_evaluation('shadow', payload)
        self.record_tool_outcome('shadow_execution', succeeded=bool(comparison.get('status_match')), notes='predicted vs actual comparison', evidence={'comparison': comparison})
        self.record_curriculum(theme='shadow_execution', skill='prediction_alignment', failure_cluster=None if comparison.get('status_match') else 'shadow_mismatch', outcome='success' if comparison.get('status_match') else 'failure')
        return {'status': 'ok', **payload}

    def review_improvement_run(self, run_id: str) -> dict:
        review = self.promotion_gate.review_run(self.workspace_root, run_id)
        payload = {'kind': 'self_improve_promotion_review', **review}
        self.kernel.record_evaluation('self-improve', payload)
        return {'status': 'ok' if review.get('approved') else 'error', **review}

    def handle(self, text: str, confirm: bool = False) -> dict:
        input_event = self.kernel.record_input('operator', {'text': text, 'confirm': confirm})
        routed = self.router.classify(text)
        proposal = self.tools.proposal_for_intent(routed.intent_type, text, proposed_by='lucifer-runtime')
        proposal_event = self.kernel.record_proposal('lucifer-runtime', proposal, parent_event_id=input_event.event_id)
        branches = self.kernel.plan_branches('branch-planner', proposal, parent_event_id=proposal_event.event_id)
        plan = self.planner.build_plan(proposal, [b.to_dict() for b in branches])
        self.kernel.record_evaluation('planner', {'kind': 'plan_summary', 'proposal_id': proposal.proposal_id, **plan}, parent_event_id=proposal_event.event_id)
        decision = self.kernel.evaluate_proposal('arc-policy', proposal, parent_event_id=proposal_event.event_id)

        if decision.decision == Decision.DENY:
            return {'status': 'denied', 'reason': decision.reason, 'branches': [b.to_dict() for b in branches], 'plan': plan}
        if decision.decision == Decision.REQUIRE_CONFIRMATION and not confirm:
            return {
                'status': 'require_confirmation',
                'reason': decision.reason,
                'proposal_id': proposal.proposal_id,
                'branches': [b.to_dict() for b in branches],
                'plan': plan,
            }

        if decision.decision == Decision.REQUIRE_CONFIRMATION and confirm:
            self.kernel.force_decision(
                'operator',
                proposal.proposal_id,
                Decision.APPROVE,
                'Operator confirmed previously gated action.',
                parent_event_id=proposal_event.event_id,
            )
        return self._execute_proposal(proposal, parent_event_id=proposal_event.event_id, branches=branches, status_hint=('approve' if decision.decision == Decision.APPROVE else 'confirmed'), plan=plan)

    def approve(self, proposal_id: str) -> dict:
        proposal = self.kernel.get_proposal(proposal_id)
        if proposal is None:
            return {'status': 'not_found', 'proposal_id': proposal_id}
        decision = self.kernel.latest_decision(proposal_id)
        if decision is None or decision.decision != Decision.REQUIRE_CONFIRMATION:
            return {'status': 'not_pending', 'proposal_id': proposal_id}
        self.kernel.force_decision('operator', proposal_id, Decision.APPROVE, 'Operator approved pending proposal.')
        branches = self.kernel.get_branch_plan(proposal_id)
        plan = self.planner.build_plan(proposal, [b.to_dict() for b in branches])
        self.kernel.record_evaluation('planner', {'kind': 'plan_summary', 'proposal_id': proposal.proposal_id, **plan})
        return self._execute_proposal(proposal, branches=branches, status_hint='confirmed', plan=plan)

    def reject(self, proposal_id: str, reason: str = 'Operator rejected pending proposal.') -> dict:
        proposal = self.kernel.get_proposal(proposal_id)
        if proposal is None:
            return {'status': 'not_found', 'proposal_id': proposal_id}
        self.kernel.force_decision('operator', proposal_id, Decision.DENY, reason)
        return {'status': 'rejected', 'proposal_id': proposal_id, 'reason': reason}

    def rollback(self, proposal_id: str) -> dict:
        receipt = self.kernel.latest_receipt(proposal_id)
        if receipt is None:
            return {'status': 'not_found', 'proposal_id': proposal_id}
        undo = receipt.outputs.get('undo')
        if not undo:
            return {'status': 'no_rollback', 'proposal_id': proposal_id}
        result = self.tools.rollback(undo)
        return {'status': 'rolled_back' if result.success else 'rollback_failed', 'proposal_id': proposal_id, 'result': result.outputs}

    def replay_state_at_receipt(self, proposal_id: str):
        receipt_event = self.kernel.log.find_latest(kind=EventKind.RECEIPT, field_name='proposal_id', value=proposal_id)
        if receipt_event is None:
            return None
        return self.kernel.state_at(receipt_event.event_id)

    def _execute_proposal(self, proposal: Proposal, parent_event_id: Optional[str] = None, branches=None, status_hint: str = 'approve', plan: dict | None = None) -> dict:
        execution_result = self.tools.execute(proposal)
        self.kernel.record_execution('lucifer-runtime', {'proposal_id': proposal.proposal_id, 'action': proposal.action, 'success': execution_result.success}, parent_event_id=parent_event_id)
        validator_results = validate_result(proposal, execution_result)
        receipt = Receipt(proposal_id=proposal.proposal_id, success=execution_result.success, outputs=execution_result.outputs, validator_results=validator_results)
        self.kernel.record_receipt('lucifer-runtime', receipt, parent_event_id=parent_event_id)
        evaluation = self.evaluator.evaluate(proposal.proposal_id, validator_results, execution_result.outputs)
        self.kernel.record_evaluation('evaluator', {'kind': 'execution_evaluation', **evaluation}, parent_event_id=parent_event_id)
        return {
            'status': status_hint,
            'proposal_id': proposal.proposal_id,
            'result': execution_result.outputs,
            'validators': validator_results,
            'branches': [b.to_dict() for b in (branches or [])],
            'plan': plan,
            'evaluation': evaluation,
        }
