from lucifer_runtime.cli import main
from model_services.interfaces import StreamEvent
from model_services import BackendRegistry
from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine


def test_cli_prompt_falls_back_to_deterministic_runtime(tmp_path, capsys):
    assert main(["--workspace", str(tmp_path), "prompt", "write notes.txt :: hello"]) == 0
    out = capsys.readouterr().out
    assert '"status": "approve"' in out
    assert '"proposal_id":' in out


def test_cli_prompt_can_use_model_path_from_env(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('ARC_LUCIFER_LLAMAFILE_BINARY', '/tmp/llamafile')
    monkeypatch.setenv('ARC_LUCIFER_LLAMAFILE_MODEL', '/tmp/model.gguf')

    calls = {'configured': False, 'prompted': False}

    from lucifer_runtime import cli as cli_module

    def fake_configure(runtime, args):
        calls['configured'] = True

    def fake_prompt_model(self, prompt, **kwargs):
        calls['prompted'] = True
        return {
            'status': 'ok',
            'backend': 'llamafile',
            'output_text': 'model says hello',
            'exact_total_tokens': 12,
        }

    monkeypatch.setattr(cli_module, '_configure_model_runtime', fake_configure)
    monkeypatch.setattr(cli_module.LuciferRuntime, 'prompt_model', fake_prompt_model, raising=False)

    assert main(["--workspace", str(tmp_path), "prompt", "hello model", "--json-output"]) == 0
    out = capsys.readouterr().out
    assert calls['configured'] is True
    assert calls['prompted'] is True
    assert 'model says hello' in out
    assert '"backend": "llamafile"' in out


class FakeStreamingBackend:
    def generate(self, prompt: str, context=None, options=None) -> str:
        return 'hello world'

    def stream_generate(self, prompt: str, context=None, options=None):
        yield StreamEvent(text='hello ', sequence=1, chars_emitted=6, words_emitted=1, estimated_tokens=1, prompt_chars=len(prompt), prompt_words=1, prompt_characters_used=len(prompt), prompt_word_tokens=1, templated_prompt_chars=len(prompt), completion_chars=6, completion_words=1, completion_characters_generated=6, completion_word_tokens=1, exact_prompt_tokens=3, exact_completion_tokens=1, exact_total_tokens=4, elapsed_seconds=0.1, chars_per_second=60.0, words_per_second=10.0, done=False)
        yield StreamEvent(text='world', sequence=2, chars_emitted=11, words_emitted=2, estimated_tokens=2, prompt_chars=len(prompt), prompt_words=1, prompt_characters_used=len(prompt), prompt_word_tokens=1, templated_prompt_chars=len(prompt), completion_chars=11, completion_words=2, completion_characters_generated=11, completion_word_tokens=2, exact_prompt_tokens=3, exact_completion_tokens=2, exact_total_tokens=5, elapsed_seconds=0.2, chars_per_second=55.0, words_per_second=10.0, done=False)
        yield StreamEvent(text='', sequence=3, chars_emitted=11, words_emitted=2, estimated_tokens=2, prompt_chars=len(prompt), prompt_words=1, prompt_characters_used=len(prompt), prompt_word_tokens=1, templated_prompt_chars=len(prompt), completion_chars=11, completion_words=2, completion_characters_generated=11, completion_word_tokens=2, exact_prompt_tokens=3, exact_completion_tokens=2, exact_total_tokens=5, elapsed_seconds=0.2, chars_per_second=55.0, words_per_second=10.0, done=True)


def test_prompt_model_records_receipt_and_completion(tmp_path):
    registry = BackendRegistry()
    registry.register('llamafile', FakeStreamingBackend())
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.sqlite3'), workspace_root=tmp_path, backend_registry=registry)
    result = runtime.prompt_model('hello', backend_name='llamafile')
    assert result['status'] == 'ok'
    assert result['output_text'] == 'hello world'
    state = runtime.kernel.state()
    assert any(item.get('kind') == 'model_prompt_complete' for item in state.evaluations)
    assert any(receipt['outputs'].get('output_text') == 'hello world' for receipt in state.receipts)
    runtime.kernel.close()
