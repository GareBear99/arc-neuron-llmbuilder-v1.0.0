# First Real Execution Milestone

The shortest honest path to a genuine translation runtime is:

1. Pick one host/guest pair.
   - Recommended: host x86_64 Linux, guest aarch64 Linux user-space CLI subset.

2. Implement one real decoder slice.
   - Enough to decode a tiny handpicked basic block set.

3. Lower into canonical IR.
   - Preserve control flow, memory effects, flags, and explicit helper boundaries.

4. Emit one runnable host block with Cranelift.
   - No full optimizer needed yet.
   - Correctness matters more than speed.

5. Add a tiny dispatch loop.
   - resolve block
   - compile or load cached block
   - execute
   - return next guest PC

6. Add block cache metadata.
   - guest start
   - block hash
   - host compatibility info
   - invalidation region metadata

7. Prove it on one sample program.
   - even a tiny CLI subset is enough
   - the repo becomes qualitatively different once one translated block actually runs
