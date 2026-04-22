# Token and text counting

The runtime now exposes **three distinct counting layers** during generation:

1. **Exact model tokens**
   - `exact_prompt_tokens`
   - `exact_completion_tokens`
   - `exact_total_tokens`

   These come from the model backend's tokenizer and final usage object.

2. **Word-based live display counters**
   - `estimated_tokens`
   - `prompt_word_tokens`
   - `completion_word_tokens`

   These are terminal-facing counters that track emitted words, not true tokenizer pieces.

3. **Character accounting**
   - `prompt_chars` / `prompt_characters_used`
   - `completion_chars` / `completion_characters_generated`

   These are exact character counts for the text sent to and produced by generation.

Use exact model token fields for billing-grade and tokenizer-true accounting.
Use word and character counters for user-visible progress and UI metrics.


## v1.2 additions

The runtime now tracks `templated_prompt_chars` separately from raw `prompt_chars`.
This is useful because the chat template applied before tokenization can materially expand the true prompt fed into the model.

Each stream event also carries:
- `elapsed_seconds`
- `chars_per_second`
- `words_per_second`

These are throughput counters for the generated completion path and are separate from the exact token totals.
