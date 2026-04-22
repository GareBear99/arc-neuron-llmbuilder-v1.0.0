# v0.7 upgrade notes

- corrected llamafile architecture to managed offline binary lifecycle
- added `LlamafileProcessManager`
- runtime now defaults to process-managed llamafile backend instead of assuming the user pre-started a server
- updated docs and example to reflect auto-launch behavior


Token counting note: v0.7's streaming field `estimated_tokens` is only a word-count estimate and is not exact.
