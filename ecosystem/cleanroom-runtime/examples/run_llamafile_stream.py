from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from model_services import BackendRegistry, LlamafileBackend, LlamafileProcessManager

# Replace these with your local paths.
LLAMAFILE_BINARY = './llamafile'
MODEL_FILE = './model.gguf'

registry = BackendRegistry()
registry.register(
    'llamafile',
    LlamafileBackend(
        process_manager=LlamafileProcessManager(
            binary_path=LLAMAFILE_BINARY,
            model_path=MODEL_FILE,
            keep_alive=True,
            startup_timeout=60.0,
        ),
        connect_timeout=60.0,
        slow_cpu_safe=True,
        stream_idle_timeout=120.0,
    ),
)

runtime = LuciferRuntime(kernel=KernelEngine(), backend_registry=registry)
for event in runtime.stream_model('Explain ARC Lucifer in one paragraph.'):
    if not event['done']:
        print(event['text'], end='', flush=True)
print()
