from __future__ import annotations

import json
import re
import time
import urllib.request
from collections.abc import Iterable, Iterator
from typing import Any, Callable

from .interfaces import StreamEvent
from .llamafile_process import LlamafileProcessManager

TransportFn = Callable[[str, bytes, dict[str, str]], Iterable[str]]
JsonPostFn = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


class LlamafileBackend:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        transport: TransportFn | None = None,
        json_post: JsonPostFn | None = None,
        process_manager: LlamafileProcessManager | None = None,
        auto_manage_process: bool = True,
        connect_timeout: float = 30.0,
        stream_idle_timeout: float | None = 120.0,
        slow_cpu_safe: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip('/') if base_url else None
        self.model = model
        self.connect_timeout = connect_timeout
        self.stream_idle_timeout = stream_idle_timeout
        self.slow_cpu_safe = slow_cpu_safe
        self.transport = transport or self._default_transport
        self.json_post = json_post or self._default_json_post
        self.process_manager = process_manager
        self.auto_manage_process = auto_manage_process

    def generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> str:
        return ''.join(event.text for event in self.stream_generate(prompt, context=context, options=options) if not event.done)

    def _count_words(self, text: str) -> int:
        return len(re.findall(r'\S+', text))

    def _prompt_metrics(self, payload: dict[str, Any], templated_prompt: str = '') -> dict[str, int]:
        combined = ''.join(str(message.get('content', '')) for message in payload.get('messages', []))
        return {
            'prompt_chars': len(combined),
            'prompt_words': self._count_words(combined),
            'templated_prompt_chars': len(templated_prompt),
        }

    def stream_generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> Iterator[StreamEvent]:
        base_url, managed_here = self._resolve_base_url()
        try:
            payload = self._build_payload(prompt, context=context, options=options)
            prompt_accounting = self.get_prompt_accounting(prompt, context=context, options=options, base_url=base_url)
            prompt_tokens = prompt_accounting['exact_prompt_tokens']
            prompt_metrics = self._prompt_metrics(payload, templated_prompt=prompt_accounting['templated_prompt'])
            lines = self.transport(
                f"{base_url}/v1/chat/completions",
                json.dumps(payload).encode('utf-8'),
                {"Content-Type": "application/json"},
            )
            yield from self._word_stream_from_lines(lines, prompt_tokens=prompt_tokens, prompt_metrics=prompt_metrics)
        finally:
            if managed_here and self.process_manager and not self.process_manager.keep_alive:
                self.process_manager.stop()

    def get_prompt_accounting(self, prompt: str, context: dict | None = None, options: dict | None = None, base_url: str | None = None) -> dict[str, Any]:
        resolved_url = base_url or self._resolve_base_url()[0]
        payload = self._build_payload(prompt, context=context, options=options)
        template_resp = self.json_post(
            f"{resolved_url}/apply-template",
            json.dumps({"messages": payload["messages"]}).encode('utf-8'),
            {"Content-Type": "application/json"},
        )
        template_prompt = str(template_resp.get('prompt', ''))
        tokenized = self.json_post(
            f"{resolved_url}/tokenize",
            json.dumps({"content": template_prompt, "add_special": False, "with_pieces": False}).encode('utf-8'),
            {"Content-Type": "application/json"},
        )
        tokens = tokenized.get('tokens', [])
        return {
            'templated_prompt': template_prompt,
            'templated_prompt_chars': len(template_prompt),
            'exact_prompt_tokens': len(tokens) if isinstance(tokens, list) else 0,
        }

    def count_prompt_tokens(self, prompt: str, context: dict | None = None, options: dict | None = None, base_url: str | None = None) -> int:
        return int(self.get_prompt_accounting(prompt, context=context, options=options, base_url=base_url)['exact_prompt_tokens'])

    def _resolve_base_url(self) -> tuple[str, bool]:
        if self.process_manager and self.auto_manage_process:
            managed = self.process_manager.ensure_running()
            return managed.base_url, True
        if self.base_url:
            return self.base_url, False
        raise RuntimeError('No llamafile runtime configured. Provide a process manager or explicit base_url.')

    def _build_payload(self, prompt: str, context: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        system_prompt = ''
        if context:
            system_prompt = str(context.get('system', ''))
        payload: dict[str, Any] = {
            'stream': True,
            'stream_options': {'include_usage': True},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
        }
        if self.model:
            payload['model'] = self.model
        if options:
            payload.update(options)
            if payload.get('stream') is True:
                merged = {'include_usage': True}
                merged.update(payload.get('stream_options') or {})
                payload['stream_options'] = merged
        return payload

    def _default_transport(self, url: str, data: bytes, headers: dict[str, str]) -> Iterable[str]:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=self.connect_timeout) as resp:  # nosec - local endpoint by design
            self._configure_stream_timeout(resp)
            for raw_line in resp:
                yield raw_line.decode('utf-8', errors='replace').strip()

    def _default_json_post(self, url: str, data: bytes, headers: dict[str, str]) -> dict[str, Any]:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=self.connect_timeout) as resp:  # nosec - local endpoint by design
            return json.loads(resp.read().decode('utf-8'))

    def _configure_stream_timeout(self, resp: Any) -> None:
        # Important: socket timeouts are per-read inactivity watchdogs, not total-generation caps.
        # As long as bytes keep arriving, the timeout resets and generation continues.
        # This is the correct invariant for slow CPUs: wait while generating, fail only on true stalls.
        target_timeout = self.stream_idle_timeout
        queue = [resp]
        visited: set[int] = set()
        while queue:
            current = queue.pop(0)
            if current is None or id(current) in visited:
                continue
            visited.add(id(current))
            settimeout = getattr(current, 'settimeout', None)
            if callable(settimeout):
                try:
                    settimeout(target_timeout)
                    return
                except Exception:
                    pass
            for attr in ('_sock', 'sock', 'fp', 'raw', '_fp'):
                child = getattr(current, attr, None)
                if child is not None:
                    queue.append(child)

    def _word_stream_from_lines(self, lines: Iterable[str], prompt_tokens: int, prompt_metrics: dict[str, int]) -> Iterator[StreamEvent]:
        buffer = ''
        sequence = 0
        chars = 0
        words = 0
        started_at = time.perf_counter()
        completion_tokens_exact: int | None = None
        total_tokens_exact: int | None = None
        prompt_chars = int(prompt_metrics.get('prompt_chars', 0))
        prompt_words = int(prompt_metrics.get('prompt_words', 0))
        templated_prompt_chars = int(prompt_metrics.get('templated_prompt_chars', 0))
        for fragment, usage in self._extract_fragments_and_usage(lines):
            if usage is not None:
                completion_tokens_exact = int(usage.get('completion_tokens', 0))
                total_tokens_exact = int(usage.get('total_tokens', prompt_tokens + completion_tokens_exact))
            if not fragment:
                continue
            buffer += fragment
            while True:
                match = re.match(r'^(\S+)(\s+)(.*)$', buffer, re.DOTALL)
                if not match:
                    break
                word, spacing, rest = match.groups()
                emitted = f"{word}{spacing}"
                chars += len(emitted)
                words += 1
                sequence += 1
                elapsed = max(time.perf_counter() - started_at, 1e-9)
                yield StreamEvent(
                    text=emitted,
                    sequence=sequence,
                    chars_emitted=chars,
                    words_emitted=words,
                    estimated_tokens=words,
                    prompt_chars=prompt_chars,
                    prompt_words=prompt_words,
                    prompt_characters_used=prompt_chars,
                    prompt_word_tokens=prompt_words,
                    templated_prompt_chars=templated_prompt_chars,
                    completion_chars=chars,
                    completion_words=words,
                    completion_characters_generated=chars,
                    completion_word_tokens=words,
                    exact_prompt_tokens=prompt_tokens,
                    exact_completion_tokens=completion_tokens_exact,
                    exact_total_tokens=total_tokens_exact,
                    elapsed_seconds=elapsed,
                    chars_per_second=chars / elapsed,
                    words_per_second=words / elapsed,
                    done=False,
                )
                buffer = rest
        if buffer:
            chars += len(buffer)
            words += 1
            sequence += 1
            elapsed = max(time.perf_counter() - started_at, 1e-9)
            yield StreamEvent(
                text=buffer,
                sequence=sequence,
                chars_emitted=chars,
                words_emitted=words,
                estimated_tokens=words,
                prompt_chars=prompt_chars,
                prompt_words=prompt_words,
                prompt_characters_used=prompt_chars,
                prompt_word_tokens=prompt_words,
                templated_prompt_chars=templated_prompt_chars,
                completion_chars=chars,
                completion_words=words,
                completion_characters_generated=chars,
                completion_word_tokens=words,
                exact_prompt_tokens=prompt_tokens,
                exact_completion_tokens=completion_tokens_exact,
                exact_total_tokens=total_tokens_exact,
                elapsed_seconds=elapsed,
                chars_per_second=chars / elapsed,
                words_per_second=words / elapsed,
                done=False,
            )
        elapsed = max(time.perf_counter() - started_at, 1e-9)
        yield StreamEvent(
            text='',
            sequence=sequence + 1,
            chars_emitted=chars,
            words_emitted=words,
            estimated_tokens=words,
            prompt_chars=prompt_chars,
            prompt_words=prompt_words,
            prompt_characters_used=prompt_chars,
            prompt_word_tokens=prompt_words,
            templated_prompt_chars=templated_prompt_chars,
            completion_chars=chars,
            completion_words=words,
            completion_characters_generated=chars,
            completion_word_tokens=words,
            exact_prompt_tokens=prompt_tokens,
            exact_completion_tokens=completion_tokens_exact,
            exact_total_tokens=total_tokens_exact,
            elapsed_seconds=elapsed,
            chars_per_second=chars / elapsed if elapsed else 0.0,
            words_per_second=words / elapsed if elapsed else 0.0,
            done=True,
        )

    def _extract_fragments_and_usage(self, lines: Iterable[str]) -> Iterator[tuple[str, dict[str, Any] | None]]:
        for line in lines:
            if not line:
                continue
            candidate = line
            if candidate.startswith('data:'):
                candidate = candidate[len('data:'):].strip()
            if candidate == '[DONE]':
                break
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            usage = payload.get('usage') if isinstance(payload.get('usage'), dict) else None
            yielded_fragment = False
            if 'choices' in payload:
                for choice in payload.get('choices', []):
                    delta = choice.get('delta') or {}
                    content = delta.get('content')
                    if isinstance(content, str):
                        yielded_fragment = True
                        yield content, usage
                    message = choice.get('message') or {}
                    alt_content = message.get('content')
                    if isinstance(alt_content, str):
                        yielded_fragment = True
                        yield alt_content, usage
            content = payload.get('content')
            if isinstance(content, str):
                yielded_fragment = True
                yield content, usage
            if usage is not None and not yielded_fragment:
                yield '', usage
