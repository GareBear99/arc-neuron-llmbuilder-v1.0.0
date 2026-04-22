# Documentation Index

This folder is the long-form technical walkthrough for ARC Lucifer Cleanroom Runtime. Read it in roughly this order if you want the cleanest path through the repo.

## Start here
- `architecture.md` — high-level system map and subsystem boundaries
- `doctrine.md` — design doctrine, constraints, and operating philosophy
- `REPO_SEO.md` — public GitHub naming, description, topics, and release positioning

## Runtime, cognition, and model flow
- `vision_runtime_optional_adapters.md` — optional perception/robotics architecture and structured world-state flow
- `llamafile_flow.md` — local-model execution path and managed llamafile flow
- `token_counting.md` — token accounting notes
- `v2_9_model_profiles_and_training.md` — model profile registry and future training/export hooks
- `v2_10_control_loops.md` — runtime control-loop additions and operational evolution
- `bluetooth_bridge.md` — optional trusted-device Bluetooth command and signal layer

## Memory and archive behavior
- `memory_retention.md` — retention logic and tier behavior
- `v2_4_memory_mirror_and_stack.md` — mirror-then-retire archive model
- `v2_5_memory_ranking_notes.md` — ranked retrieval and planning feed-in

## Self-improvement, repair, and resilience
- `v2_0_self_improve_runs.md` — self-improvement baseline
- `v2_3_autonomous_patch_cycle.md` — deterministic patch/validate/promote cycle
- `v2_6_candidate_cycles.md` — multi-candidate generation, scoring, and selection
- `v2_7_adversarial_cycles.md` — adversarial and fault-injection coverage
- `v2_2_resilience_and_comments.md` — resilience, fallback handling, and operator comments
- `v2_9_1_fixnet_archive_embedding.md` — FixNet archive embedding and mirror behavior

## Code operator, evaluation, and release posture
- `v2_1_code_operator.md` — exact line/symbol editing and code operator boundaries
- `benchmarks.md` — benchmark direction and next measurable tiers
- `source_comparison.md` — comparison framing versus other approaches
- `migration_plan.md` — migration and rollout framing

## Upgrade history
- `v0_4_upgrade_notes.md` through `v2_10_control_loops.md` — chronological evolution notes across the project

## Suggested reading paths

### For first-time GitHub visitors
1. `architecture.md`
2. `vision_runtime_optional_adapters.md`
3. `doctrine.md`
4. `llamafile_flow.md`
5. `memory_retention.md`
6. `v2_3_autonomous_patch_cycle.md`

### For memory/archive design
1. `memory_retention.md`
2. `v2_4_memory_mirror_and_stack.md`
3. `v2_5_memory_ranking_notes.md`

### For self-improvement and safety posture
1. `v2_0_self_improve_runs.md`
2. `v2_3_autonomous_patch_cycle.md`
3. `v2_6_candidate_cycles.md`
4. `v2_7_adversarial_cycles.md`

### For public release positioning
1. `REPO_SEO.md`
2. `source_comparison.md`
3. `benchmarks.md`

- [Runtime modularization](runtime_modularization.md)
