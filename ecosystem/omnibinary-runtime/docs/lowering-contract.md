# Lowering Contract

Canonical lowering is complete only when decoded guest operations become typed IR values and control-flow with:
- stable SSA/value assignment
- explicit helper calls
- syscall boundary markers
- deopt/re-entry markers
- comparison against fixture expectations
