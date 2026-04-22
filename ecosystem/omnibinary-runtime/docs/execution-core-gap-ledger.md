# Execution Core Gap Ledger

This repo is still missing the true execution center required for a production binary translation runtime:

- real guest ISA decoder
- real canonical lowering from decoded guest blocks into `obi-ir`
- real Cranelift-emitted runnable host blocks
- translated block cache reuse + invalidation
- syscall personality mediation
- sandbox/broker execution plane
- supported-machine compile/test validation

Until those land, the repo should be described as a production-track scaffold, not a finished universal runtime.
