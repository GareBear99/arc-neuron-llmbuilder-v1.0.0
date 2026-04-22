# v1.1 upgrade notes

- Separated exact model-token counts from word-based display counters.
- Added explicit prompt/completion character and word accounting on every stream event.
- Preserved `estimated_tokens` as a live word-based display estimate for terminal UX.
- Added tests for prompt/completion accounting.
