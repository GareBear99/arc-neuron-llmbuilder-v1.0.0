"""Model orchestration mixin for LuciferRuntime."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterator

from arc_kernel.schemas import Capability, Decision, Proposal, Receipt, RiskLevel
from model_services import LlamafileBackend, LlamafileProcessManager, StreamEvent


class RuntimeModelMixin:
    def configure_llamafile(
        self,
        *,
        binary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        host: str = '127.0.0.1',
        port: int | None = None,
        startup_timeout: float = 20.0,
        idle_timeout: float | None = 120.0,
        keep_alive: bool = True,
        model_name: str | None = None,
        auto_manage_process: bool = True,
    ) -> None:
        manager = LlamafileProcessManager(
            binary_path=binary_path,
            model_path=model_path,
            host=host,
            port=port,
            startup_timeout=startup_timeout,
            keep_alive=keep_alive,
        )
        backend = LlamafileBackend(
            model=model_name,
            process_manager=manager,
            auto_manage_process=auto_manage_process,
            stream_idle_timeout=idle_timeout,
        )
        self.backends.register('llamafile', backend)

    def stream_model(self, prompt: str, backend_name: str = 'llamafile', context: dict | None = None, options: dict | None = None) -> Iterator[dict]:
        # legacy generator kept for compatibility; no receipt/proposal lifecycle.
        input_event = self.kernel.record_input('operator', {'model_prompt': prompt, 'backend': backend_name})
        backend = self.backends.get(backend_name)
        self.kernel.record_evaluation('model-services', {'kind': 'stream_start', 'backend': backend_name, 'prompt_chars': len(prompt)}, parent_event_id=input_event.event_id)
        last_event: StreamEvent | None = None
        for event in backend.stream_generate(prompt, context=context, options=options):
            last_event = event
            payload = self._payload_from_stream_event(event)
            payload['hud'] = self.render_stream_hud(payload)
            if not event.done:
                self.kernel.record_evaluation('model-services', {'kind': 'stream_chunk', 'backend': backend_name, **payload}, parent_event_id=input_event.event_id)
            yield payload
        if last_event is None:
            last_event = StreamEvent(text='', sequence=0, chars_emitted=0, words_emitted=0, estimated_tokens=0, done=True)
        self.kernel.record_evaluation('model-services', {'kind': 'stream_complete', 'backend': backend_name, **self._payload_from_stream_event(last_event), 'session_totals': self._accumulate_session_metrics(last_event)}, parent_event_id=input_event.event_id)

    def prompt_model(
        self,
        prompt: str,
        *,
        backend_name: str = 'llamafile',
        context: dict | None = None,
        options: dict | None = None,
        stream: bool = False,
        on_chunk: Callable[[dict], None] | None = None,
    ) -> dict:
        input_event = self.kernel.record_input('operator', {'model_prompt': prompt, 'backend': backend_name})
        proposal = Proposal(
            action='model_prompt',
            capability=Capability(
                name='model.generate',
                description='Local model generation',
                risk=RiskLevel.LOW,
                side_effects=[],
                validators=[],
                dry_run_supported=False,
                requires_confirmation=False,
            ),
            params={'prompt': prompt, 'backend': backend_name},
            proposed_by='lucifer-runtime',
            rationale='Model prompt execution',
        )
        proposal_event = self.kernel.record_proposal('lucifer-runtime', proposal, parent_event_id=input_event.event_id)
        decision = self.kernel.evaluate_proposal('arc-policy', proposal, parent_event_id=proposal_event.event_id)
        if decision.decision == Decision.DENY:
            return {'status': 'denied', 'reason': decision.reason, 'proposal_id': proposal.proposal_id}

        backend = self.backends.get(backend_name)
        self.kernel.record_execution('lucifer-runtime', {'proposal_id': proposal.proposal_id, 'action': 'model_prompt', 'success': True, 'backend': backend_name, 'started': True}, parent_event_id=proposal_event.event_id)
        chunks: list[str] = []
        final_payload: dict | None = None
        interrupted = False
        interrupt_reason = ''
        try:
            for event in backend.stream_generate(prompt, context=context, options=options):
                payload = self._payload_from_stream_event(event)
                payload['hud'] = self.render_stream_hud(payload)
                payload['proposal_id'] = proposal.proposal_id
                payload['backend'] = backend_name
                final_payload = payload
                if payload.get('text'):
                    chunks.append(payload['text'])
                if not event.done:
                    self.kernel.record_evaluation('model-services', {'kind': 'stream_chunk', 'proposal_id': proposal.proposal_id, 'backend': backend_name, **payload}, parent_event_id=proposal_event.event_id)
                    if stream and on_chunk is not None:
                        on_chunk(payload)
                else:
                    self.kernel.record_evaluation('model-services', {'kind': 'stream_complete', 'proposal_id': proposal.proposal_id, 'backend': backend_name, **payload}, parent_event_id=proposal_event.event_id)
        except KeyboardInterrupt as exc:
            interrupted = True
            interrupt_reason = 'Operator interrupted local generation.'
            failure = self.failure_classifier.classify_exception(exc)
        except Exception as exc:  # pragma: no cover - defensive runtime path
            interrupted = True
            failure = self.failure_classifier.classify_exception(exc)
            interrupt_reason = f'Model generation failed: {exc}'
            fallback_mode = self.fallback_selector.choose(failure, 'model_prompt')
            if fallback_mode == 'deterministic_router':
                return self._complete_via_deterministic_fallback(prompt, interrupt_reason, proposal.proposal_id, parent_event_id=proposal_event.event_id)
            if fallback_mode == 'echo_stub':
                self._record_fallback(task_kind='model_prompt', proposal_id=proposal.proposal_id, original_mode='managed_llamafile', fallback_mode='echo_stub', reason=interrupt_reason, parent_event_id=proposal_event.event_id)
                stub_text = f'[fallback-echo] {prompt}'
                receipt = Receipt(
                    proposal_id=proposal.proposal_id,
                    success=True,
                    outputs={'backend': 'echo_stub', 'output_text': stub_text},
                    validator_results=[{'validator': 'fallback_echo_completed', 'passed': True}],
                )
                self.kernel.record_receipt('lucifer-runtime', receipt, parent_event_id=proposal_event.event_id)
                return {'status': 'completed_fallback', 'proposal_id': proposal.proposal_id, 'backend': 'echo_stub', 'output_text': stub_text, 'fallback_mode': 'echo_stub', 'fallback_reason': interrupt_reason}
        final_payload = dict(final_payload or {})
        final_payload['output_text'] = ''.join(chunks)
        final_payload['backend'] = backend_name
        final_payload['proposal_id'] = proposal.proposal_id
        final_payload['session_metrics'] = self.get_session_metrics()
        if interrupted:
            fallback_mode = self.fallback_selector.choose(failure, 'model_prompt')
            if fallback_mode == 'echo_stub':
                self._record_fallback(task_kind='model_prompt', proposal_id=proposal.proposal_id, original_mode='managed_llamafile', fallback_mode='echo_stub', reason=interrupt_reason, parent_event_id=proposal_event.event_id)
                final_payload['status'] = 'completed_fallback'
                final_payload['fallback_mode'] = 'echo_stub'
                final_payload['fallback_reason'] = interrupt_reason
                final_payload['output_text'] = final_payload.get('output_text') or f'[fallback-echo] {prompt}'
                receipt = Receipt(
                    proposal_id=proposal.proposal_id,
                    success=True,
                    outputs={'backend': 'echo_stub', 'output_text': final_payload['output_text']},
                    validator_results=[{'validator': 'fallback_echo_completed', 'passed': True}],
                )
                self.kernel.record_receipt('lucifer-runtime', receipt, parent_event_id=proposal_event.event_id)
                return final_payload
            if fallback_mode == 'deterministic_router':
                return self._complete_via_deterministic_fallback(prompt, interrupt_reason, proposal.proposal_id, parent_event_id=proposal_event.event_id)
            final_payload['status'] = 'interrupted'
            final_payload['fallback_reason'] = interrupt_reason
        else:
            final_payload['status'] = 'ok'
        event_payload = self._dict_to_stream_event(final_payload)
        self._accumulate_session_metrics(event_payload)
        self.kernel.record_evaluation('model-services', {
            'kind': 'stream_session_summary',
            'proposal_id': proposal.proposal_id,
            'backend': backend_name,
            'output_text': final_payload['output_text'],
            'completion_chars': final_payload.get('completion_chars'),
            'completion_words': final_payload.get('completion_words'),
            'exact_prompt_tokens': final_payload.get('exact_prompt_tokens'),
            'exact_completion_tokens': final_payload.get('exact_completion_tokens'),
            'exact_total_tokens': final_payload.get('exact_total_tokens'),
            'session_totals': self.get_session_metrics(),
        }, parent_event_id=proposal_event.event_id)
        receipt = Receipt(
            proposal_id=proposal.proposal_id,
            success=True,
            outputs={
                'backend': backend_name,
                'output_text': final_payload['output_text'],
                'exact_prompt_tokens': final_payload.get('exact_prompt_tokens'),
                'exact_completion_tokens': final_payload.get('exact_completion_tokens'),
                'exact_total_tokens': final_payload.get('exact_total_tokens'),
                'completion_chars': final_payload.get('completion_chars'),
                'completion_words': final_payload.get('completion_words'),
            },
            validator_results=[{'validator': 'model_prompt_completed', 'passed': True}],
        )
        self.kernel.record_receipt('lucifer-runtime', receipt, parent_event_id=proposal_event.event_id)
        self.kernel.record_evaluation('model-services', {
            'kind': 'model_prompt_complete',
            'proposal_id': proposal.proposal_id,
            'backend': backend_name,
            'output_text': final_payload['output_text'],
            'exact_total_tokens': final_payload.get('exact_total_tokens'),
        }, parent_event_id=proposal_event.event_id)
        return final_payload

    def _record_fallback(self, *, task_kind: str, proposal_id: str | None, original_mode: str, fallback_mode: str, reason: str, parent_event_id: str | None = None) -> None:
        """Persist fallback history so degraded completion is inspectable later."""
        record = self.continuations.finish(self.continuations.start(task_kind, fallback_mode, reason), 'completed_fallback')
        self.kernel.record_evaluation('resilience', {
            'kind': 'fallback_event',
            'task_kind': task_kind,
            'proposal_id': proposal_id,
            'original_mode': original_mode,
            'fallback_mode': fallback_mode,
            'reason': reason,
            **record.to_dict(),
        }, parent_event_id=parent_event_id)

    def _complete_via_deterministic_fallback(self, prompt: str, failure_reason: str, proposal_id: str, parent_event_id: str | None = None) -> dict:
        """Fallback from model generation to the deterministic router when the prompt is command-like."""
        fallback_mode = 'deterministic_router'
        self._record_fallback(task_kind='model_prompt', proposal_id=proposal_id, original_mode='managed_llamafile', fallback_mode=fallback_mode, reason=failure_reason, parent_event_id=parent_event_id)
        result = self.handle(prompt, confirm=False)
        result['status'] = 'completed_fallback'
        result['fallback_mode'] = fallback_mode
        result['fallback_reason'] = failure_reason
        result['proposal_id'] = proposal_id
        return result

    def _payload_from_stream_event(self, event: StreamEvent) -> dict:
        return {
            'text': event.text,
            'sequence': event.sequence,
            'chars_emitted': event.chars_emitted,
            'words_emitted': event.words_emitted,
            'estimated_tokens': event.estimated_tokens,
            'prompt_chars': event.prompt_chars,
            'prompt_words': event.prompt_words,
            'prompt_characters_used': event.prompt_characters_used,
            'prompt_word_tokens': event.prompt_word_tokens,
            'templated_prompt_chars': event.templated_prompt_chars,
            'completion_chars': event.completion_chars,
            'completion_words': event.completion_words,
            'completion_characters_generated': event.completion_characters_generated,
            'completion_word_tokens': event.completion_word_tokens,
            'exact_prompt_tokens': event.exact_prompt_tokens,
            'exact_completion_tokens': event.exact_completion_tokens,
            'exact_total_tokens': event.exact_total_tokens,
            'elapsed_seconds': event.elapsed_seconds,
            'chars_per_second': event.chars_per_second,
            'words_per_second': event.words_per_second,
            'done': event.done,
        }

    def _dict_to_stream_event(self, payload: dict) -> StreamEvent:
        return StreamEvent(
            text=payload.get('text', ''),
            sequence=int(payload.get('sequence', 0)),
            chars_emitted=int(payload.get('chars_emitted', 0)),
            words_emitted=int(payload.get('words_emitted', 0)),
            estimated_tokens=int(payload.get('estimated_tokens', 0)),
            prompt_chars=int(payload.get('prompt_chars', 0)),
            prompt_words=int(payload.get('prompt_words', 0)),
            prompt_characters_used=int(payload.get('prompt_characters_used', 0)),
            prompt_word_tokens=int(payload.get('prompt_word_tokens', 0)),
            templated_prompt_chars=int(payload.get('templated_prompt_chars', 0)),
            completion_chars=int(payload.get('completion_chars', 0)),
            completion_words=int(payload.get('completion_words', 0)),
            completion_characters_generated=int(payload.get('completion_characters_generated', 0)),
            completion_word_tokens=int(payload.get('completion_word_tokens', 0)),
            exact_prompt_tokens=int(payload.get('exact_prompt_tokens') or 0),
            exact_completion_tokens=int(payload.get('exact_completion_tokens') or 0),
            exact_total_tokens=int(payload.get('exact_total_tokens') or 0),
            elapsed_seconds=float(payload.get('elapsed_seconds', 0.0)),
            chars_per_second=float(payload.get('chars_per_second', 0.0)),
            words_per_second=float(payload.get('words_per_second', 0.0)),
            done=bool(payload.get('done', False)),
        )

    def _accumulate_session_metrics(self, event: StreamEvent) -> dict:
        self.session_metrics['requests'] += 1
        self.session_metrics['prompt_chars'] += event.prompt_chars
        self.session_metrics['prompt_words'] += event.prompt_words
        self.session_metrics['templated_prompt_chars'] += event.templated_prompt_chars
        self.session_metrics['completion_chars'] += event.completion_chars
        self.session_metrics['completion_words'] += event.completion_words
        self.session_metrics['exact_prompt_tokens'] += int(event.exact_prompt_tokens or 0)
        self.session_metrics['exact_completion_tokens'] += int(event.exact_completion_tokens or 0)
        self.session_metrics['exact_total_tokens'] += int(event.exact_total_tokens or 0)
        return dict(self.session_metrics)

    def get_session_metrics(self) -> dict:
        return dict(self.session_metrics)

    def render_stream_hud(self, payload: dict) -> str:
        return (
            f"seq={payload.get('sequence', 0)} | prompt chars={payload.get('prompt_chars', 0)}"
            f" | template chars={payload.get('templated_prompt_chars', 0)}"
            f" | out chars={payload.get('completion_chars', 0)} | out words={payload.get('completion_words', 0)}"
            f" | exact tokens={payload.get('exact_total_tokens')} | cps={payload.get('chars_per_second', 0.0):.2f}"
            f" | wps={payload.get('words_per_second', 0.0):.2f}"
        )
