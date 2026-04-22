# Execution Slice Plan

This document narrows the remaining engineering work into the smallest honest slice that turns OmniBinary from a strong scaffold into a real translated execution runtime.

## Slice 1
- Guest: Linux aarch64 user-space CLI subset
- Host: Linux x86_64
- Decoder: one straight-line basic block
- Lowering: canonical IR only
- Emitter: Cranelift baseline only
- Syscalls: deny by default, allow a tiny explicit subset

## Success criteria
- decode one real block
- lower one real block
- emit one runnable host block
- execute through a guarded harness
- persist one translated block receipt and cache record

## Non-goals
- full process execution
- full syscall surface
- self-modifying code
- signals, threads, TLS, or vector completeness
