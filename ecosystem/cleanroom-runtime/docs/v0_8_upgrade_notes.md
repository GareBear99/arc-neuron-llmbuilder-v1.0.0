# v0.8 upgrade notes

- exact prompt token preflight added via `/apply-template` + `/tokenize`
- final exact completion and total token counts added from streamed `usage` chunk
- `estimated_tokens` kept only as a live display estimate during streaming
- runtime stream payload now includes `exact_prompt_tokens`, `exact_completion_tokens`, and `exact_total_tokens`
