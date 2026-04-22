# Runtime Modularization (v2.15.0)

This pass reduced authority concentration inside `src/lucifer_runtime/runtime.py` without changing the public `LuciferRuntime` API.

## What changed

- `runtime.py` now focuses on core runtime identity, proposal handling, directive continuity, FixNet/trust/curriculum bookkeeping, and execution receipts.
- `runtime_model.py` now owns local-model orchestration, streaming payload conversion, fallback completion, and session metrics.
- `runtime_code.py` now owns code-edit flows and the self-improvement patch/candidate/promotion lifecycle.

## Why it matters

Before this pass, `runtime.py` was the largest concentrated authority in the package. That made the runtime harder to audit, reason about, and evolve. Splitting the model and code/self-improve paths into dedicated mixins keeps the public shell stable while reducing the trust surface of any one file.

## What did not change

- `LuciferRuntime` method names and CLI behavior remain stable.
- Optional robotics, mapping, spatial truth, and geo overlay layers remain optional.
- The runtime still preserves receipts, replay, rollback, fallback history, and policy gating.

## Remaining next step

The next highest-value decomposition target is still the cognition/perception side of the stack, especially any oversized authorities that accumulate too much policy and inference behavior in a single module.
