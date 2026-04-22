# Release Gates

## Gate 0 — Honest Scaffold
Required:
- repo structure exists
- docs explain truth boundary
- native lane works for same-host binaries
- receipt cache is functional

## Gate 1 — First Translation Proof
Required:
- real guest decoder for one ISA pair
- canonical IR lowering for one basic block
- Cranelift host emission for one executable block
- dispatch loop preview upgraded to real dispatch path

## Gate 2 — Repeated Execution
Required:
- translated block cache reuse
- invalidation metadata
- crash/context receipts from translated execution
- minimal syscall mediation for supported sample programs

## Gate 3 — Controlled Compatibility Surface
Required:
- documented compatibility matrix
- one personality adapter with working sample coverage
- sandbox separation between controller and execution plane
- CI proving supported host/toolchain combinations

## Gate 4 — Production Candidate
Required:
- packaging/signing
- release notes discipline
- security hardening review
- adversarial input testing
- benchmark and regression harness
