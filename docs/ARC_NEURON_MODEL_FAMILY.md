# ARC-Neuron Model Family

ARC-Neuron is the model family built around ARC Cognition Core.

## Current baseline
- **ARC-Neuron Tiny 0.05M v0.1 (F32, GGUF)**
- Purpose: end-to-end proof that the ARC stack can train, export, validate, load, and run a local GGUF artifact.
- Status: working local baseline, not a flagship capability model.

## Family ladder
- **ARC-Neuron Tiny** — lab proof, container validation, runtime smoke, regression floor
- **ARC-Neuron Base** — first usable small instruction model
- **ARC-Neuron Core** — main local general model
- **ARC-Neuron Command** — command routing, planning, tool discipline
- **ARC-Neuron Language** — language and transliteration specialization
- **ARC-Neuron Native** — deployment build packaged for local native runtime

## What Tiny proves
1. Repo-local training can emit a real `.gguf` file.
2. The `.gguf` can be validated without external services.
3. The runner can load the artifact and generate text locally.
4. ARC Cognition Core can act as the control plane around the artifact.

## What Tiny does not claim
- competitive frontier capability
- llama.cpp compatibility for this toy architecture
- a finished production flagship

## Release doctrine
Every ARC-Neuron release should ship with:
- a model card
- a GGUF artifact
- a validation receipt
- a benchmark report
- a provenance manifest
- a runtime launch path

## Next hard step
Promote from ARC-Neuron Tiny to ARC-Neuron Base by plugging a stronger upstream checkpoint into the production build path already present in this repo.
