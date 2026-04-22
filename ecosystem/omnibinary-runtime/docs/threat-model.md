# Threat Model

## Core risks
- malformed or hostile binaries
- cache poisoning or stale cache reuse
- in-process crashes from unsafe execution backends
- over-claiming support and causing unsafe execution assumptions

## Current mitigations
- explicit support-level receipts
- no foreign execution backend yet
- append-only receipt index
- explicit production-gap documentation

## Required future mitigations
- process isolation for execution and JIT workers
- signed cache artifacts or strong integrity metadata
- syscall brokering and capability gating
- fuzzing for intake and decoder layers
