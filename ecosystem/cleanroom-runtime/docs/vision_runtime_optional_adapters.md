# Vision Runtime and Optional Adapter Doctrine

This repository does **not** require cameras, microphones, depth sensors, robot SDKs, simulators, or multimodal model stacks to install or run.

That is deliberate. The core runtime should stay useful as a deterministic local operator shell even on minimal systems.

## Principle

Perception and embodiment are treated as **optional adapters**:
- optional to install
- optional to enable
- optional to swap
- still governed by the same runtime receipts, memory, verification, and continuity rules

## Why this matters

Many autonomy projects fail in one of two ways:
1. they stay as text-only wrappers with no path to real-world state
2. they hard-wire giant vision/robotics stacks into the base product and make the system brittle, heavy, and unclear

This repo is choosing a third path:
- keep the base runtime deterministic and dependency-light
- define clean contracts for optional perception/action layers
- let the cognition core reason over **structured world state** instead of raw sensor floods

## Recommended flow

```text
SENSORS / INPUTS
  -> OPTIONAL PERCEPTION ADAPTERS
  -> STRUCTURED OBSERVATIONS
  -> WORLD MODEL / MEMORY UPDATE
  -> GGUF OR LOCAL MODEL PLANNER
  -> BOUNDED ACTION PLAN
  -> VERIFIER / SAFETY CHECKS
  -> OPTIONAL ACTION OR ROBOTICS ADAPTERS
  -> RECEIPTS / RESULT / CONTINUITY UPDATE
```

## What belongs in the GGUF core

Good use of the local model:
- planning
- semantic interpretation
- goal decomposition
- uncertainty reasoning
- choosing between bounded actions

Bad use of the local model:
- millisecond motor control
- direct servo stabilization
- collision timing
- unconstrained actuator writes

The model should act as the executive planner, not as the low-level reflex loop.

## Adapter contract

The repo now includes `src/perception_adapters/` with generic contracts for:
- sensor packets
- structured observations
- optional adapter configuration
- perception adapters
- action adapters
- registry/description surfaces

These are intentionally generic so the same runtime can later support:
- desktop capture
- webcam or phone camera
- OCR
- audio event detection
- simulation bridges
- rover/arm/body adapters

## Packaging posture

Optional extras exist for users who want to experiment with richer layers:
- `.[vision]`
- `.[audio]`
- `.[robotics]`
- `.[embodiment]`
- `.[full]`

The base install remains clean and light.

## Public-facing claim

The honest claim is:

> ARC Lucifer Cleanroom Runtime is a deterministic local autonomy foundation with optional perception and embodiment adapters, not a finished AGI or robotics product.

That framing is stronger because it is true, modular, and extensible.
