# Execution Backlog

This is the shortest path to the first real translated execution milestone.

## Phase 1
- real guest decoder for one ISA pair
- canonical IR lowering from real decoded guest blocks
- Cranelift baseline emission for one block shape
- dispatch loop re-entry for a minimal translated block

## Phase 2
- translated block cache persistence
- invalidation metadata for writable code pages
- helper-call plumbing for memory and syscall boundaries

## Phase 3
- Linux personality mediation for a narrow user-space subset
- sandbox broker process model
- crash/fault propagation receipts across translated execution
