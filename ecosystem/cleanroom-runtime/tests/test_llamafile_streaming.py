from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from model_services import BackendRegistry
from model_services.llamafile_backend import LlamafileBackend
from model_services.llamafile_process import LlamafileProcessManager


class FakeManager:
    def __init__(self):
        self.ensure_calls = 0
        self.keep_alive = True

    def ensure_running(self):
        self.ensure_calls += 1
        class Managed:
            base_url = 'http://127.0.0.1:8081'
        return Managed()


def test_llamafile_streaming_emits_words_and_exact_final_usage(tmp_path):
    def fake_transport(url, data, headers):
        return [
            'data: {"choices":[{"delta":{"content":"Hello "}}]}',
            'data: {"choices":[{"delta":{"content":"world from "}}]}',
            'data: {"choices":[{"delta":{"content":"llamafile"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":5,"total_tokens":17}}',
            'data: [DONE]',
        ]

    def fake_json_post(url, data, headers):
        if url.endswith('/apply-template'):
            return {'prompt': '<s>[INST] Say hello. [/INST]'}
        if url.endswith('/tokenize'):
            return {'tokens': [1] * 12}
        raise AssertionError(url)

    registry = BackendRegistry()
    registry.register('llamafile', LlamafileBackend(transport=fake_transport, json_post=fake_json_post, process_manager=FakeManager()))
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path, backend_registry=registry)
    events = list(runtime.stream_model('Say hello.'))

    texts = [event['text'] for event in events if not event['done']]
    assert texts == ['Hello ', 'world ', 'from ', 'llamafile']
    assert events[-1]['done'] is True
    assert events[-1]['chars_emitted'] == len('Hello world from llamafile')
    assert events[-1]['words_emitted'] == 4
    assert events[-1]['estimated_tokens'] == 4
    assert events[-1]['prompt_chars'] == len('Say hello.')
    assert events[-1]['prompt_words'] == 2
    assert events[-1]['prompt_characters_used'] == len('Say hello.')
    assert events[-1]['prompt_word_tokens'] == 2
    assert events[-1]['completion_chars'] == len('Hello world from llamafile')
    assert events[-1]['completion_words'] == 4
    assert events[-1]['completion_characters_generated'] == len('Hello world from llamafile')
    assert events[-1]['completion_word_tokens'] == 4
    assert events[-1]['exact_prompt_tokens'] == 12
    assert events[-1]['exact_completion_tokens'] == 5
    assert events[-1]['exact_total_tokens'] == 17


def test_runtime_defaults_to_llamafile_only(tmp_path):
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path)
    assert runtime.backends.names() == ['llamafile']


def test_backend_auto_starts_managed_llamafile_process():
    manager = FakeManager()

    def fake_transport(url, data, headers):
        assert url.startswith('http://127.0.0.1:8081/v1/chat/completions')
        return [
            'data: {"choices":[{"delta":{"content":"Hi "}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":1,"total_tokens":4}}',
            'data: [DONE]',
        ]

    def fake_json_post(url, data, headers):
        if url.endswith('/apply-template'):
            return {'prompt': 'test'}
        if url.endswith('/tokenize'):
            return {'tokens': [1, 2, 3]}
        raise AssertionError(url)

    backend = LlamafileBackend(transport=fake_transport, json_post=fake_json_post, process_manager=manager)
    events = list(backend.stream_generate('test'))
    assert manager.ensure_calls == 1
    assert events[-1].done is True
    assert events[-1].exact_prompt_tokens == 3
    assert events[-1].exact_completion_tokens == 1
    assert events[-1].exact_total_tokens == 4


def test_process_manager_resolves_explicit_missing_path():
    manager = LlamafileProcessManager(binary_path='./nonexistent-llamafile')
    assert manager.binary_path.name == 'nonexistent-llamafile'


class _SocketLike:
    def __init__(self):
        self.timeout = 'unset'

    def settimeout(self, value):
        self.timeout = value


class _RawLike:
    def __init__(self, sock):
        self._sock = sock


class _FpLike:
    def __init__(self, raw):
        self.raw = raw


class _RespLike:
    def __init__(self, sock):
        self.fp = _FpLike(_RawLike(sock))


def test_backend_applies_idle_timeout_in_slow_cpu_safe_mode():
    backend = LlamafileBackend(slow_cpu_safe=True, stream_idle_timeout=123.0)
    sock = _SocketLike()
    backend._configure_stream_timeout(_RespLike(sock))
    assert sock.timeout == 123.0


def test_backend_can_disable_idle_timeout_explicitly():
    backend = LlamafileBackend(slow_cpu_safe=True, stream_idle_timeout=None)
    sock = _SocketLike()
    backend._configure_stream_timeout(_RespLike(sock))
    assert sock.timeout is None


def test_prompt_metrics_ignore_empty_system_prompt():
    backend = LlamafileBackend(transport=lambda *args, **kwargs: [], json_post=lambda *args, **kwargs: {'tokens': []}, process_manager=FakeManager())
    metrics = backend._prompt_metrics({'messages': [{'role': 'system', 'content': ''}, {'role': 'user', 'content': 'hello there'}]})
    assert metrics['prompt_chars'] == len('hello there')
    assert metrics['prompt_words'] == 2


def test_stream_payload_includes_template_chars_throughput_and_hud(tmp_path):
    def fake_transport(url, data, headers):
        return [
            'data: {"choices":[{"delta":{"content":"Hello "}}]}',
            'data: {"choices":[{"delta":{"content":"again"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":4,"completion_tokens":2,"total_tokens":6}}',
            'data: [DONE]',
        ]

    def fake_json_post(url, data, headers):
        if url.endswith('/apply-template'):
            return {'prompt': '<s>[INST] hello [/INST]'}
        if url.endswith('/tokenize'):
            return {'tokens': [1, 2, 3, 4]}
        raise AssertionError(url)

    registry = BackendRegistry()
    registry.register('llamafile', LlamafileBackend(transport=fake_transport, json_post=fake_json_post, process_manager=FakeManager()))
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path, backend_registry=registry)
    events = list(runtime.stream_model('hello'))
    final = events[-1]
    assert final['templated_prompt_chars'] == len('<s>[INST] hello [/INST]')
    assert final['elapsed_seconds'] >= 0.0
    assert final['chars_per_second'] >= 0.0
    assert final['words_per_second'] >= 0.0
    assert 'template chars=' in final['hud']


def test_session_metrics_accumulate_across_stream_requests(tmp_path):
    def fake_transport(url, data, headers):
        return [
            'data: {"choices":[{"delta":{"content":"Hi "}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
            'data: [DONE]',
        ]

    def fake_json_post(url, data, headers):
        if url.endswith('/apply-template'):
            body = data.decode('utf-8')
            return {'prompt': body}
        if url.endswith('/tokenize'):
            return {'tokens': [1, 2]}
        raise AssertionError(url)

    registry = BackendRegistry()
    registry.register('llamafile', LlamafileBackend(transport=fake_transport, json_post=fake_json_post, process_manager=FakeManager()))
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path, backend_registry=registry)
    list(runtime.stream_model('one'))
    list(runtime.stream_model('two'))
    metrics = runtime.get_session_metrics()
    assert metrics['requests'] == 2
    assert metrics['completion_words'] == 2
    assert metrics['exact_total_tokens'] == 6
