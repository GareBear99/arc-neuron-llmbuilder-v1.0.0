# Self-Fill Authority Arbitration

This layer scores competing self-fill candidates using live `source_weights`, candidate confidence, candidate status, and a surface-type factor.

Score formula:

`effective_score = confidence × source_weight × status_weight × surface_weight`

Goals:
- prefer higher-authority sources for equivalent surfaces
- keep canonical truth explicit
- avoid blind auto-promotion of weak candidates
- write repeatable arbitration receipts before promotion

New CLI commands:
- `arbitrate-self-fill-candidates`
- `list-self-fill-arbitration-runs`
- `list-self-fill-arbitration-decisions`
- `promote-arbitrated-self-fill`
- `recommend-source-weight`

Typical flow:
1. stage candidates with `self-fill-gap-scan` and approved source importers
2. inspect source weights with `list-source-weights`
3. adjust weights with `recommend-source-weight` or `set-source-weight`
4. run `arbitrate-self-fill-candidates`
5. review decision receipts
6. run `promote-arbitrated-self-fill` once the threshold is acceptable
