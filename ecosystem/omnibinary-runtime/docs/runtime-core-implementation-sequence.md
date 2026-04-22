# Runtime Core Implementation Sequence

1. Real decoder crate for one guest ISA
2. Decode into translation blocks
3. Lower translation blocks into canonical IR
4. Emit host code with Cranelift
5. Execute via small dispatch loop
6. Add translated-block cache metadata
7. Add invalidation on code mutation / policy mismatch
8. Add syscall personality for the supported target
9. Add sandbox/broker process split
10. Validate on supported machines with evidence pack
