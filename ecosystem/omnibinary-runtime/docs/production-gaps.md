
# Production Gaps

OmniBinary Runtime v0.6 is not production-ready.

## What exists
- workspace layout
- intake and format classification
- host detection
- lane selection
- native execution proof path
- receipt persistence/indexing
- planning IR receipt path
- lowering preview path with translation-block summaries and compilation preview metadata
- toy decode preview path from input bytes into canonical IR-like operations
- dispatch preview path with block sequencing and invalidation watchpoints

## What blocks production
- no real foreign guest decoder
- no real DBT execution loop
- no Cranelift code emission wired to runtime execution
- no syscall personality mediation beyond planning surface
- no sandbox broker process
- no compile validation in this packaging environment
- no fuzzing, stress, perf, or compatibility suite
- no signed release and packaging workflow

## Honest status
This repo is a strong architectural and repo foundation with decode/dispatch previews, not a finished universal runtime.


## Still open after v0.7
- config is advisory, not a hardened signed policy layer
- cache stats are operational only, not integrity-enforced
- support inventory is static and does not validate backend availability


## New v0.8 framing
The repo now includes release gates and acceptance criteria. This reduces ambiguity, but it does not eliminate the hard engineering gaps. The center of gravity is still the first real translation milestone: one actual guest decoder plus one actual emitted host block.
