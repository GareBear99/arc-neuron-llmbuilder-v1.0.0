# ARC Lucifer Cleanroom Runtime Architecture

ARC Lucifer Cleanroom Runtime is organized as a deterministic operator runtime with separated responsibilities and a strong bias toward continuity, auditability, and bounded autonomy.

## System goal

The system is designed to keep a long-lived local operator shell coherent across runs. It does that by separating directive handling, runtime state, planning, execution, verification, memory retention, and repair lineage instead of collapsing everything into one opaque model session.

## Major subsystems

- `arc_kernel/` — event authority, receipts, policy recording, replay, rollback, branching, persistence
- `lucifer_runtime/` — CLI surface, routing, command handling, operator-facing execution layer
- `cognition_services/` — goals, planning, evaluation, directives, trust, world-model oriented helpers
- `model_services/` — local model configuration, profiles, interfaces, and managed execution paths
- `memory_subsystem/` — hot/warm/archive tiers, mirroring, ranking, retrieval, retirement behavior
- `perception_adapters/` — optional vision, audio, simulator, and robotics adapter contracts that keep the core runtime dependency-light
- `self_improve/` — scaffolded runs, candidate generation, scoring, execution, promotion, adversarial testing
- `code_editing/` — exact range and symbol-grounded code manipulation flows
- `fixnet/` — repair lineage, novelty filtering, semantic fix objects, archive mirrors
- `resilience/` — degraded modes, fallbacks, continuation, retry budgets, operational hardening
- `verifier/` — validation surfaces and safe promotion checks
- `dashboards/` — monitoring and trace inspection helpers

## Control flow

```text
Directive input
  -> continuity / runtime boot
  -> state + world-model load
  -> goal compile / planning
  -> action routing
  -> receipt / result capture
  -> verification / evaluation / shadow compare
  -> trust + curriculum + FixNet update
  -> memory/archive update
  -> continuity save
```

## Design priorities

1. Deterministic runtime behavior where possible
2. Receipts and auditability over silent mutation
3. Replay and rollback as first-class operational tools
4. Memory that remains readable and rankable
5. Bounded self-improvement instead of unconstrained mutation
6. Open-ended backend integration without giving up runtime authority
7. Fallback-aware operation rather than brittle single-path execution

## Current boundary

The repository is a strong technical foundation. Perception and robotics are now framed as optional capability layers rather than mandatory assumptions. Real-world production maturity still depends on external soak testing, hardware validation, adapter implementations, installer packaging, and chosen model benchmarking.
