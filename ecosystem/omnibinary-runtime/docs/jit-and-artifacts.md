
# JIT and Artifact Direction

v0.5 adds a **lowering preview** stage.

It still does not emit runnable machine code, but it now captures the metadata that the future runtime should preserve:
- translation block boundaries
- invalidation triggers
- host backend target
- helper-call count
- syscall-bearing block detection
- cache key hints for future compiled artifacts

## Intended next engineering step
1. Decode one real guest basic block.
2. Lower it into the canonical IR.
3. Compile it through a real Cranelift function builder.
4. Store compiled-block metadata in the persistent cache.
5. Re-enter through a runtime dispatch loop.
