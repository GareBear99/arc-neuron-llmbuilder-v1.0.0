# v2.10 Control Loop Closures

This upgrade closes three missing repo-side loops without pretending the runtime is finished AGI:

- Goal compiler: operator intent now compiles into a structured goal contract with constraints, invariants, evidence requirements, and archive mode.
- Shadow execution: predicted vs actual status/key comparison now records a measurable confidence score.
- Promotion court: self-improvement promotion now requires a reviewable evidence bundle instead of a single implicit gate.

These additions keep the runtime deterministic while making the loop more explicit and auditable.
