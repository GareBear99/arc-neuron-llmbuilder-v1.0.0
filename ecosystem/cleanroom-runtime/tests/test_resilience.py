from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine


class BoomBackend:
    def stream_generate(self, prompt, context=None, options=None):
        raise RuntimeError('connection refused by local model backend')


def test_prompt_falls_back_to_deterministic_router(tmp_path):
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.sqlite3'), workspace_root=tmp_path)
    runtime.backends.register('llamafile', BoomBackend())
    result = runtime.prompt_model('write note.txt :: hi', backend_name='llamafile')
    assert result['status'] == 'completed_fallback'
    assert result['fallback_mode'] == 'deterministic_router'
    assert (tmp_path / 'note.txt').read_text() == 'hi'
    state = runtime.kernel.state()
    assert state.fallback_events


def test_code_symbol_suffix_match(tmp_path):
    target = tmp_path / 'sample.py'
    target.write_text('class A:\n    def method(self):\n        return 1\n')
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.sqlite3'), workspace_root=tmp_path)
    result = runtime.code_replace_symbol('sample.py', 'method', '    def method(self):\n        return 2')
    assert result['status'] == 'ok'
    assert 'return 2' in target.read_text()
