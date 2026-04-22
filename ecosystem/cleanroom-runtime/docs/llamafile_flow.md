# Llamafile offline binary flow

## Correct runtime model

The user should **not** start a separate server by hand.

ARC Lucifer treats **llamafile as the local inference binary**. Under the hood, llamafile may expose a loopback HTTP endpoint, but the runtime owns that lifecycle itself:

1. Resolve the llamafile binary path.
2. Resolve the model path if one is configured.
3. Launch llamafile as a managed local process when the first generation request arrives.
4. Wait for the loopback endpoint to become ready.
5. Stream output through the managed process.
6. Coalesce raw fragments into readable word-sized emissions.
7. Record stream telemetry into ARC.
8. Keep the process warm or stop it based on policy.

From the user's perspective, it is **offline local execution from the binary**, not "go boot a server first."

## User flow

1. User installs or ships the `llamafile` binary and a local model file.
2. User points ARC Lucifer at those paths in config or CLI flags.
3. User runs ARC Lucifer.
4. User submits a prompt.
5. Runtime auto-launches llamafile if it is not already running.
6. Runtime streams word-sized chunks immediately into the terminal.
7. ARC records:
   - `stream_start`
   - `stream_chunk`
   - `stream_complete`
8. Runtime can keep the binary warm for the next prompt or shut it down.

## Timeout model

The runtime now uses **split timeout rules**:

- `startup_timeout`: only for launching the binary and waiting for readiness.
- `connect_timeout`: only for establishing the generation request.
- **no fixed total generation timeout** in slow-CPU-safe mode.
- `stream_idle_timeout`: an inactivity watchdog on the live stream socket. It resets on every incoming chunk.
- the stream only times out when **no bytes arrive** for the configured idle window.

That means long prompts or slow token generation can continue for as long as the model is still producing output. If the model or stream truly stalls, the idle watchdog trips instead of hanging forever.

## Counter meaning

- `chars_emitted`: exact running character count
- `words_emitted`: exact running word count based on emitted units
- `estimated_tokens`: live display estimate only
- `exact_prompt_tokens`: exact tokenizer-backed prompt count
- `exact_completion_tokens`: exact final completion count from backend usage
- `exact_total_tokens`: exact final total token count from backend usage

## Important behavior

Socket timeouts here are **per-read inactivity timeouts**, not total wall-clock generation limits. If llamafile streams tokens/chunks correctly, every incoming chunk resets the timer. That is why this mode waits while generation is alive and only fails when generation has actually stopped producing output.
