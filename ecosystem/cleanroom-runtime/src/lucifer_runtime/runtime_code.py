"""Code editing and self-improvement orchestration mixin for LuciferRuntime."""

from __future__ import annotations

from arc_kernel.schemas import Capability, Decision, Proposal, Receipt, RiskLevel
from code_editing import PatchKind, PatchOperation


class RuntimeCodeMixin:
    def run_benchmarks(self) -> dict:
        payload = self.benchmarks.run_smoke_suite(self.workspace_root)
        self.kernel.record_evaluation('self-improve', payload)
        return {'result': 'ok', **payload}

    def analyze_improvements(self) -> dict:
        state = self.kernel.state()
        payload = self.improvement_analyzer.analyze(state, self.workspace_root)
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_analysis', **payload})
        return payload

    def plan_improvements(self, target_key: str | None = None) -> dict:
        state = self.kernel.state()
        analysis = self.improvement_analyzer.analyze(state, self.workspace_root)
        payload = self.improvement_planner.build_plan(analysis, self.workspace_root, target_key=target_key)
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_plan', **payload})
        return payload

    def scaffold_improvement_run(self, target_key: str | None = None) -> dict:
        plan = self.plan_improvements(target_key=target_key)
        run = self.sandbox_manager.scaffold(self.workspace_root, plan)
        payload = {'kind': 'self_improve_run', 'plan': plan, **run.to_dict()}
        self.kernel.record_evaluation('self-improve', payload)
        return {'status': 'ok', 'plan': plan, 'run': run.to_dict()}

    def code_index(self, path: str) -> dict:
        payload = self.code_planner.plan_for_path(self.workspace_root, path, instruction='index file')
        self.kernel.record_evaluation('code-edit', {'kind': 'code_index', **payload})
        return payload

    def code_verify(self, path: str) -> dict:
        result = self.code_verifier.verify_file(self.workspace_root / path)
        payload = {'status': 'ok', **result}
        self.kernel.record_evaluation('code-edit', {'kind': 'code_verify', **payload})
        return payload

    def code_plan(self, path: str, instruction: str, symbol_name: str | None = None) -> dict:
        payload = self.code_planner.plan_for_path(self.workspace_root, path, instruction=instruction, symbol_name=symbol_name)
        self.kernel.record_evaluation('code-edit', {'kind': 'code_plan', **payload})
        return payload

    def code_replace_range(self, path: str, start_line: int, end_line: int, replacement_text: str, *, confirm: bool = False, expected_hash: str | None = None, reason: str = '') -> dict:
        proposal = Proposal(
            action='code_replace_range',
            capability=Capability(
                name='code.patch',
                description='Exact line-anchored code patch',
                risk=RiskLevel.MEDIUM,
                side_effects=['mutates code files'],
                validators=['line_anchor', 'workspace_guard', 'python_parse'],
                dry_run_supported=False,
                requires_confirmation=False,
            ),
            params={'path': path, 'start_line': start_line, 'end_line': end_line},
            proposed_by='lucifer-runtime',
            rationale=reason or 'Exact line-anchored code edit',
        )
        proposal_event = self.kernel.record_proposal('code-edit', proposal)
        branches = self.kernel.plan_branches('branch-planner', proposal, parent_event_id=proposal_event.event_id)
        plan = self.planner.build_plan(proposal, [b.to_dict() for b in branches])
        self.kernel.record_evaluation('planner', {'kind': 'plan_summary', 'proposal_id': proposal.proposal_id, **plan}, parent_event_id=proposal_event.event_id)
        decision = self.kernel.evaluate_proposal('arc-policy', proposal, parent_event_id=proposal_event.event_id)
        if decision.decision == Decision.DENY:
            return {'status': 'denied', 'reason': decision.reason, 'proposal_id': proposal.proposal_id}
        if decision.decision == Decision.REQUIRE_CONFIRMATION and not confirm:
            return {'status': 'require_confirmation', 'proposal_id': proposal.proposal_id, 'reason': decision.reason}
        if decision.decision == Decision.REQUIRE_CONFIRMATION and confirm:
            self.kernel.force_decision('operator', proposal.proposal_id, Decision.APPROVE, 'Operator confirmed code patch.', parent_event_id=proposal_event.event_id)
        result = self.patch_engine.apply(self.workspace_root, PatchOperation(kind=PatchKind.REPLACE_RANGE, path=path, replacement_text=replacement_text, start_line=start_line, end_line=end_line, expected_hash=expected_hash, reason=reason))
        self.kernel.record_execution('code-edit', {'proposal_id': proposal.proposal_id, 'action': proposal.action, 'success': result.success, 'path': path}, parent_event_id=proposal_event.event_id)
        receipt = Receipt(proposal_id=proposal.proposal_id, success=result.success, outputs=result.to_dict(), validator_results=result.verification['checks'])
        self.kernel.record_receipt('code-edit', receipt, parent_event_id=proposal_event.event_id)
        result_failure = self.failure_classifier.classify_patch_result(result.to_dict())
        if result_failure is not None:
            fallback_mode = self.fallback_selector.choose(result_failure, 'code_patch')
            if fallback_mode:
                self._record_fallback(task_kind='code_patch', proposal_id=proposal.proposal_id, original_mode='replace_range', fallback_mode=fallback_mode, reason=result_failure.reason, parent_event_id=proposal_event.event_id)
        self.kernel.record_evaluation('code-edit', {'kind': 'code_patch', 'proposal_id': proposal.proposal_id, **result.to_dict()}, parent_event_id=proposal_event.event_id)
        return {'status': 'ok' if result.success else 'completed_fallback', 'proposal_id': proposal.proposal_id, 'result': result.to_dict(), 'branches': [b.to_dict() for b in branches], 'plan': plan}

    def code_replace_symbol(self, path: str, symbol_name: str, replacement_text: str, *, confirm: bool = False, expected_hash: str | None = None, reason: str = '') -> dict:
        proposal = Proposal(
            action='code_replace_symbol',
            capability=Capability(
                name='code.patch',
                description='Exact symbol-anchored code patch',
                risk=RiskLevel.MEDIUM,
                side_effects=['mutates code files'],
                validators=['symbol_anchor', 'workspace_guard', 'python_parse'],
                dry_run_supported=False,
                requires_confirmation=False,
            ),
            params={'path': path, 'symbol_name': symbol_name},
            proposed_by='lucifer-runtime',
            rationale=reason or 'Exact symbol-anchored code edit',
        )
        proposal_event = self.kernel.record_proposal('code-edit', proposal)
        branches = self.kernel.plan_branches('branch-planner', proposal, parent_event_id=proposal_event.event_id)
        plan = self.planner.build_plan(proposal, [b.to_dict() for b in branches])
        self.kernel.record_evaluation('planner', {'kind': 'plan_summary', 'proposal_id': proposal.proposal_id, **plan}, parent_event_id=proposal_event.event_id)
        decision = self.kernel.evaluate_proposal('arc-policy', proposal, parent_event_id=proposal_event.event_id)
        if decision.decision == Decision.DENY:
            return {'status': 'denied', 'reason': decision.reason, 'proposal_id': proposal.proposal_id}
        if decision.decision == Decision.REQUIRE_CONFIRMATION and not confirm:
            return {'status': 'require_confirmation', 'proposal_id': proposal.proposal_id, 'reason': decision.reason}
        if decision.decision == Decision.REQUIRE_CONFIRMATION and confirm:
            self.kernel.force_decision('operator', proposal.proposal_id, Decision.APPROVE, 'Operator confirmed code patch.', parent_event_id=proposal_event.event_id)
        try:
            result = self.patch_engine.apply(self.workspace_root, PatchOperation(kind=PatchKind.REPLACE_SYMBOL, path=path, replacement_text=replacement_text, symbol_name=symbol_name, expected_hash=expected_hash, reason=reason))
        except Exception as exc:
            failure = self.failure_classifier.classify_exception(exc)
            fallback_mode = self.fallback_selector.choose(failure, 'code_patch')
            if fallback_mode == 'scaffold_manual_fix':
                self._record_fallback(task_kind='code_patch', proposal_id=proposal.proposal_id, original_mode='replace_symbol', fallback_mode=fallback_mode, reason=failure.reason, parent_event_id=proposal_event.event_id)
                return {'status': 'partial_fallback', 'proposal_id': proposal.proposal_id, 'reason': failure.reason, 'fallback_mode': fallback_mode, 'branches': [b.to_dict() for b in branches], 'plan': plan}
            raise
        self.kernel.record_execution('code-edit', {'proposal_id': proposal.proposal_id, 'action': proposal.action, 'success': result.success, 'path': path, 'symbol_name': symbol_name}, parent_event_id=proposal_event.event_id)
        receipt = Receipt(proposal_id=proposal.proposal_id, success=result.success, outputs=result.to_dict(), validator_results=result.verification['checks'])
        self.kernel.record_receipt('code-edit', receipt, parent_event_id=proposal_event.event_id)
        result_failure = self.failure_classifier.classify_patch_result(result.to_dict())
        if result_failure is not None:
            fallback_mode = self.fallback_selector.choose(result_failure, 'code_patch')
            if fallback_mode == 'scaffold_manual_fix':
                self._record_fallback(task_kind='code_patch', proposal_id=proposal.proposal_id, original_mode='replace_symbol', fallback_mode=fallback_mode, reason=result_failure.reason, parent_event_id=proposal_event.event_id)
        self.kernel.record_evaluation('code-edit', {'kind': 'code_patch', 'proposal_id': proposal.proposal_id, **result.to_dict()}, parent_event_id=proposal_event.event_id)
        return {'status': 'ok' if result.success else 'completed_fallback', 'proposal_id': proposal.proposal_id, 'result': result.to_dict(), 'branches': [b.to_dict() for b in branches], 'plan': plan}

    def apply_improvement_patch(
        self,
        run_id: str,
        *,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
        validation_requested: bool = False,
    ) -> dict:
        """Apply a grounded patch inside a self-improvement worktree and record the result."""
        payload = self.improvement_executor.apply_patch(
            self.workspace_root,
            run_id,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            validation_requested=validation_requested,
            rationale=rationale,
        ).to_dict()
        event = {'kind': 'self_improve_patch', **payload}
        self.kernel.record_evaluation('self-improve', event)
        return {'status': 'ok', **payload}

    def execute_improvement_cycle(
        self,
        run_id: str,
        *,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
        validate: bool = True,
        timeout: int = 120,
        promote: bool = False,
        force_promote: bool = False,
        quarantine_on_failure: bool = True,
    ) -> dict:
        """Run a full sandbox patch cycle: patch, validate, and optionally promote."""
        payload = self.improvement_executor.execute_cycle(
            self.workspace_root,
            run_id,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            rationale=rationale,
            validate=validate,
            timeout=timeout,
            promote=promote,
            force_promote=force_promote,
            quarantine_on_failure=quarantine_on_failure,
        )
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_cycle', **payload})
        return payload

    def validate_improvement_run(self, run_id: str, timeout: int = 120) -> dict:
        result = self.promotion_gate.validate_run(self.workspace_root, run_id, timeout=timeout)
        payload = {'kind': 'self_improve_validation', **result.to_dict()}
        self.kernel.record_evaluation('self-improve', payload)
        self.record_tool_outcome('self_improve_validation', succeeded=result.passed, notes=f'validation run {run_id}', evidence={'validation': result.to_dict()})
        self.record_curriculum(theme='self_improve', skill='validation', failure_cluster=None if result.passed else 'validation_failure', outcome='success' if result.passed else 'failure', notes=run_id)
        if not result.passed:
            failing = [c for c in result.command_results if not c.get('passed')]
            first = failing[0] if failing else {}
            signature = f"run:{run_id}|cmd:{first.get('command','unknown')}|rc:{first.get('returncode')}"
            emitted = self.fixnet_register(
                title='Self-improve validation failure',
                error_type='self_improve_validation',
                error_signature=signature,
                solution='Adjust patch and/or add regression tests until recommended_commands pass.',
                summary='Auto-emitted from PromotionGate validation failure.',
                keywords=['fixnet', 'self-improve', 'validation'],
                context={'run_id': run_id, 'failing_commands': failing},
                evidence={'validation': result.to_dict()},
                linked_run_ids=[run_id],
                auto_embed=True,
            )
            if emitted.get('fix'):
                self.fixnet_sync_archive(emitted['fix']['fix_id'], status='live')
        return {'status': 'ok', **result.to_dict()}

    def promote_improvement_run(self, run_id: str, *, force: bool = False) -> dict:
        try:
            result = self.promotion_gate.promote_run(self.workspace_root, run_id, force=force)
        except Exception as exc:
            emitted = self.fixnet_register(
                title='Self-improve promotion failure',
                error_type='self_improve_promotion',
                error_signature=f"run:{run_id}|force:{force}|exc:{type(exc).__name__}",
                solution='Fix validation failures or adjust evidence bundle before promotion.',
                summary=str(exc),
                keywords=['fixnet', 'self-improve', 'promotion'],
                context={'run_id': run_id, 'force': force},
                evidence={'exception': repr(exc)},
                linked_run_ids=[run_id],
                auto_embed=True,
            )
            self.record_tool_outcome('self_improve_promotion', succeeded=False, notes=f'promotion failed for {run_id}', evidence={'exception': repr(exc)})
            self.record_curriculum(theme='self_improve', skill='promotion', failure_cluster='promotion_failure', outcome='failure', notes=run_id)
            if emitted.get('fix'):
                self.fixnet_sync_archive(emitted['fix']['fix_id'], status='live')
            payload = {'kind': 'self_improve_promotion', 'run_id': run_id, 'forced': force, 'error': str(exc), 'exception': type(exc).__name__}
            self.kernel.record_evaluation('self-improve', payload)
            return {'status': 'error', **payload}
        payload = {'kind': 'self_improve_promotion', **result}
        self.kernel.record_evaluation('self-improve', payload)
        self.record_tool_outcome('self_improve_promotion', succeeded=True, notes=f'promotion succeeded for {run_id}', evidence={'promotion': result})
        self.record_curriculum(theme='self_improve', skill='promotion', failure_cluster=None, outcome='success', notes=run_id)
        return {'status': 'ok', **result}

    def generate_improvement_candidates(
        self,
        run_id: str,
        *,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
    ) -> dict:
        payload = self.candidate_cycles.generate_candidates(
            self.workspace_root,
            run_id,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            rationale=rationale,
        )
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_candidates', **payload})
        return payload

    def score_improvement_candidates(self, run_id: str, *, timeout: int = 120) -> dict:
        payload = self.candidate_cycles.score_candidates(self.workspace_root, run_id, timeout=timeout)
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_candidate_scores', **payload})
        top = payload.get('best_candidate') or {}
        self.record_curriculum(theme='self_improve', skill='candidate_scoring', failure_cluster=None if top else 'missing_candidate_scores', outcome='success' if top else 'failure', notes=run_id)
        if top:
            self.fixnet_register(
                title='Self-improve candidate scoring',
                error_type='self_improve_candidates',
                error_signature=f"run:{run_id}|candidate:{top.get('candidate_id','unknown')}",
                solution='Prefer the highest-scoring validated candidate or iterate on failing variants.',
                summary='Auto-emitted from candidate scoring.',
                keywords=['fixnet','self-improve','candidates'],
                context={'run_id': run_id, 'best_candidate': top},
                evidence={'candidate_scores': payload},
                linked_run_ids=[run_id],
            )
        return payload

    def inject_improvement_fault(self, run_id: str, *, kind: str, path: str | None = None, note: str = '') -> dict:
        payload = self.adversarial.inject_fault(self.workspace_root, run_id, kind=kind, path=path, note=note).to_dict()
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_fault', **payload})
        return {'status': 'ok', **payload}

    def run_improvement_adversarial_cycle(
        self,
        run_id: str,
        *,
        kind: str,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
        timeout: int = 120,
    ) -> dict:
        payload = self.adversarial.adversarial_cycle(
            self.workspace_root,
            run_id,
            kind=kind,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            rationale=rationale,
            timeout=timeout,
        )
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_adversarial_cycle', **payload})
        return payload

    def choose_best_improvement_candidate(self, run_id: str) -> dict:
        payload = self.candidate_cycles.choose_best_candidate(self.workspace_root, run_id)
        self.kernel.record_evaluation('self-improve', {'kind': 'self_improve_best_candidate', **payload})
        if payload.get('candidate_id'):
            self.record_curriculum(theme='self_improve', skill='candidate_selection', outcome='success', notes=run_id)
            self.fixnet_register(
                title='Self-improve best candidate selected',
                error_type='self_improve_best_candidate',
                error_signature=f"run:{run_id}|candidate:{payload.get('candidate_id')}",
                solution='Promote only after review and successful validation.',
                summary='Auto-emitted from best-candidate selection.',
                keywords=['fixnet','self-improve','best-candidate'],
                context={'run_id': run_id, 'candidate': payload},
                evidence={'best_candidate': payload},
                linked_run_ids=[run_id],
            )
        return payload

    def execute_best_improvement_candidate(
        self,
        run_id: str,
        *,
        timeout: int = 120,
        promote: bool = False,
        force_promote: bool = False,
        quarantine_on_failure: bool = True,
    ) -> dict:
        best = self.choose_best_improvement_candidate(run_id)
        if best.get('status') != 'ok':
            return best
        candidate = best['best_candidate']
        manifest = self.candidate_cycles.load_manifest(self.workspace_root, run_id)
        candidate_spec = next((item for item in manifest.get('candidates', []) if item.get('candidate_id') == candidate.get('candidate_id')), None)
        if candidate_spec is None:
            return {'status': 'not_found', 'run_id': run_id, 'reason': 'Best candidate missing from manifest.'}
        return self.execute_improvement_cycle(
            run_id,
            path=candidate_spec['path'],
            replacement_text=candidate_spec['replacement_text'],
            symbol_name=candidate_spec.get('symbol_name'),
            start_line=candidate_spec.get('start_line'),
            end_line=candidate_spec.get('end_line'),
            expected_hash=candidate_spec.get('expected_hash'),
            rationale=candidate_spec.get('rationale', ''),
            validate=True,
            timeout=timeout,
            promote=promote,
            force_promote=force_promote,
            quarantine_on_failure=quarantine_on_failure,
        )
