# The ARC Ecosystem

ARC-Neuron LLMBuilder does not live alone. It is one surface of a larger family of governed, local-first systems, each owning a single frozen role. This document is the authoritative index.

## Overview

| Repo | Role in the system | Governance contribution |
|---|---|---|
| **[ARC-Core](https://github.com/GareBear99/ARC-Core)** | Signal intelligence platform — proposal, evidence, authority-gating | Canonical source-of-truth event + receipt spine |
| **[arc-lucifer-cleanroom-runtime](https://github.com/GareBear99/arc-lucifer-cleanroom-runtime)** | Deterministic local-first AI operator runtime | Event-sourced kernel, directive continuity, bounded execution |
| **[arc-cognition-core](https://github.com/GareBear99/arc-cognition-core)** | Cognition lab for building, benchmarking, shaping, promoting models | Promotion gate lineage, GGUF-oriented evaluation doctrine |
| **[arc-language-module](https://github.com/GareBear99/arc-language-module)** | Governed multilingual language backend | Canonical lexical truth, provenance, readiness states |
| **[omnibinary-runtime](https://github.com/GareBear99/omnibinary-runtime)** | Native-first binary intake / classification / execution-fabric | Indexed binary mirror / runtime-ledger substrate |
| **[Arc-RAR](https://github.com/GareBear99/Arc-RAR)** | CLI-first archive manager with native-app control | Restorable archive / rollback bundle format |
| **[ARC-Neuron-LLMBuilder](https://github.com/GareBear99/ARC-Neuron-LLMBuilder)** *(this repo)* | Governed local AI build-and-memory system | Canonical conversation pipeline, Gate v2, floor model, reflection, absorption |

## Frozen roles — who owns what

The single most important rule across the ecosystem: **roles never swap**. Every component has one responsibility; nothing else in the stack may claim that role.

- **ARC-Core** owns authoritative event truth. Every receipt in the system derives from its discipline.
- **Cleanroom Runtime** owns deterministic execution. Bounded continuity, directives, replay, rollback — all operate through its kernel.
- **Cognition Core** owns the model-growth lab. Training, benchmarking, promotion of cognition candidates live here.
- **Language Module** owns canonical truth for language itself. Terms, aliases, corrections, provenance.
- **OmniBinary** owns the binary mirror of source truth. Runtime-ledger semantics, decode, dispatch, execution fabric.
- **Arc-RAR** owns restorable archive lineage. Every promoted candidate ends up in a manifest-indexed bundle here.
- **ARC-Neuron LLMBuilder** (this repo) owns the governed local build loop: train → benchmark → gate → archive → verify, with conversation-driven corpus harvesting and reflection-assisted response shaping.

## How LLMBuilder integrates with siblings

### Source truth flow
1. A conversation turn through the canonical pipeline in LLMBuilder produces a `ConversationRecord` with SHA-256 receipts.
2. The record is mirrored into the **OmniBinary** runtime-ledger direction via `runtime/learning_spine.py` using the OBIN v2 indexed format.
3. Training-eligible records are exported as SFT corpora that feed the next governed candidate in **Cognition Core's** doctrine.
4. Terms absorbed from the conversation enter the **Language Module**'s governed truth surface with provenance and trust ranks.
5. Promoted candidates are bundled into **Arc-RAR** archives with full lineage preserved.
6. Every decision receipt traces back to the **ARC-Core** event/receipt spine.
7. The **Cleanroom Runtime** direction provides the deterministic operator shell this whole loop eventually operates inside.

### Role contract summary

```
ARC-Core            = event / receipt / authority spine
Cleanroom Runtime   = deterministic operator kernel
Cognition Core      = model-growth lab
Language Module     = canonical lexical truth
OmniBinary          = binary mirror / runtime ledger
Arc-RAR             = archive / rollback bundles
ARC-Neuron LLMBuilder = governed build loop + conversation pipeline + Gate v2
```

## Status snapshot (v1.0.0-governed era)

| Repo | Public status | Maturity notes |
|---|---|---|
| ARC-Core | public | Signal intelligence scaffold, audit-report-led development |
| Cleanroom Runtime | public | Event-sourced kernel with directive continuity |
| Cognition Core | public | Cognition lab with benchmarking and promotion flow |
| Language Module | public | Governed multilingual substrate with provenance |
| OmniBinary | public | Binary intake / execution-fabric scaffold |
| Arc-RAR | public | CLI-first archive with native-app control |
| **ARC-Neuron LLMBuilder** | **public** | **v1.0.0-governed — doctrine closed, three governed promotions on record** |

## Contributing across the ecosystem

Issues or pull requests that affect more than one repo should:
- Open a tracking issue in **ARC-Neuron LLMBuilder** (as the integration surface) and link it to the per-repo sub-issues.
- Keep role boundaries intact — do not cross-own logic between repos.
- Preserve receipts. Any cross-repo state change must be addressable after the fact.

## Sponsoring the work

All seven repositories share a single author and a single funding target. If the governance doctrine, local-first philosophy, or the evidence-backed promotion loop is useful to you:

- **GitHub Sponsors**: https://github.com/sponsors/GareBear99
- **Direct contribution**: open issues and PRs in whichever repo addresses your use case

Sponsorship funds time for:
- Hardening the existing governance across all seven repos
- Benchmark-breadth expansion
- Integration between adjacent roles (OmniBinary ↔ LLMBuilder, ARC-Core ↔ Cleanroom)
- External-model adapter validation at larger tiers
- Production documentation for enterprise adoption

## One-line summary

**One author, one doctrine, seven frozen roles. Each repo owns its single responsibility. Together they form a governed local AI operating system.**
