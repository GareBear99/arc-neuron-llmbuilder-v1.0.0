# Implementation Backlog

This document turns the remaining execution-core work into concrete tracks. Use `obi impl-backlog` for the machine-readable version.

## Tracks
- Decoder
- Lowering
- Emission
- Runtime
- Validation

## Shortest path
Decode one real guest block, lower it, emit one runnable host block, re-enter through a tiny dispatch loop, then validate on a supported machine.
