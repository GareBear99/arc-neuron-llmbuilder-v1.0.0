# ARC-Core

**Adaptive Reasoning Core** is a deterministic event-and-decision kernel for ingesting signals, resolving entities, building graph state, managing cases, simulating proposals, handling geospatial overlays, and enforcing authority-gated execution. 

Inspired by ARC-OS (2067) from the TV series 'Continuum' filmed in Vancouver B.C.

This repository is the **system-of-record layer** in the wider Gary Doman ecosystem. It is the kernel that future operator surfaces, visualization layers, autonomous runtimes, archive systems, and Synth-grade cognition interfaces are meant to sit on top of.

## What this repository is

ARC-Core is not a generic chat wrapper and not a freeform agent shell.

It is a structured intelligence-console foundation built around:
- canonical events
- replayable state transitions
- entity and graph tracking
- proposal workflows
- case management
- analyst notes
- tamper-evident receipts
- authority-gated actions
- geospatial structures, geofences, tracks, and evidence export
- optional model augmentation without surrendering canonical control

In practical terms, this repo currently ships a working **FastAPI-backed ARC console prototype** with HTML dashboard pages, SQLite persistence, test coverage, auth/session flows, proposals, watchlists, cases, connectors, notebook entries, receipts, and indoor-geospatial estimation primitives.

## Why ARC-Core matters in the larger stack

The wider stack is not meant to be a pile of disconnected repos. ARC-Core is the truth spine that gives the rest of the ecosystem shared memory, bounded execution, and structured authority.

### Related repositories in the stack

- [Proto-AGI](https://github.com/GareBear99/Proto-AGI) — broader AGI architecture framing and ecosystem doctrine
- [ARC-Core](https://github.com/GareBear99/ARC-Core) — canonical event, graph, proposal, case, and receipt kernel
- [ARC-Turbo-OS](https://github.com/GareBear99/ARC-Turbo-OS) — seeded runtime / branch-aware execution direction for turbo resolution and reusable computation
- [Arc-RAR](https://github.com/GareBear99/Arc-RAR) — native archive / package / transfer layer for moving deterministic state and artifacts across systems
- [Proto-Synth_Grid_Engine](https://github.com/GareBear99/Proto-Synth_Grid_Engine) — future embodiment / visualization / structured cognition surface
- [Seeded-Universe-Recreation-Engine](https://github.com/GareBear99/Seeded-Universe-Recreation-Engine) — long-range seeded simulation target where ARC-style truth handling becomes critical
- [LuciferAI_Local](https://github.com/GareBear99/LuciferAI_Local) — local model/runtime experimentation layer that can plug into ARC without replacing ARC authority
- [AGI_Photon-Quantum-Computing](https://github.com/GareBear99/AGI_Photon-Quantum-Computing) — future compute substrate and SSOT-oriented control theory for high-speed cognition infrastructure

### Stack role

```text
AGI_Photon-Quantum-Computing
        ↓
ARC-Turbo-OS
        ↓
ARC-Core
        ↓
LuciferAI_Local / model adapters / bounded workers
        ↓
Proto-Synth_Grid_Engine
        ↓
Seeded-Universe-Recreation-Engine / future ARC-native applications
```

ARC-Core sits in the middle because it owns:
- event truth
- receipt chains
- case/proposal lifecycle
- authority boundaries
- canonical graph state
- branchable reasoning inputs
- evidence export

## Current feature surface

The current repository (ARC-Core) contains a functional prototype with the following major areas:

### API and application surface
- FastAPI service entrypoint
- CORS-controlled demo mode
- mounted HTML UI
- health and manifest endpoints
- auth bootstrap, login, and session resolution

### Event and graph pipeline
- event ingest and listing
- entity resolution and normalization
- entity details with related events and notes
- graph snapshots
- timeline views
- risk-score prioritization

### Analyst workflow
- watchlists
- cases
- case-event attachment
- proposals
- approval flow
- notebook / notes

### Evidence and trust
- audit log
- tamper-evident receipt chain
- receipt verification endpoint
- signed receipt support
- evidence export bundle

### Connector and ingest extensions
- filesystem JSONL connector sources
- connector polling and run history
- demo feed bootstrap

### Geospatial / spatial intelligence surface
- structures and sensors
- geofences
- blueprint overlays
- calibration profiles
- track estimation
- track import
- latest tracks
- heatmap generation
- incident creation and listing
- evidence pack export

### UI pages included
- dashboard
- signals
- graph
- timeline
- cases
- geo

## Read-first audit summary

This package was read and inventoried before documentation changes.

### Code-surface counts
- **39 Python files** in the reconstructed working package
- **161 functions**
- **18 classes**
- **13 passing tests** after reconstruction of the split bundle

### Important repo reality
The root zip includes both:
- a lightweight visible top-level scaffold, and
- a **split-bundle package** that contains the full working ARC console implementation.

The complete working repo is reconstructed by combining the split bundle parts inside `ARC-Core_GitHub_split_bundle/`.

That is why this README now documents the **actual full code surface**, not just the minimal root scaffold.

## Repository structure

```text
ARC-Core-main/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CODE_SURFACE_AUDIT.md
│   ├── REPO_SETUP_CHECKLIST.md
│   ├── SEO_PROMOTION.md
│   └── STACK.md
├── ARC_Console/
│   ├── arc/
│   │   ├── api/
│   │   ├── core/
│   │   ├── geo/
│   │   ├── services/
│   │   └── ui/
│   ├── data/
│   ├── tests/
│   ├── run_arc.py
│   └── requirements.txt
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── workflows/ci.yml
└── ARC-Core_GitHub_split_bundle/
    └── split upload parts for GitHub-safe assembly
```

## How to run

### Local setup

```bash
cd ARC_Console
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_arc.py
```

Then open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/ui/dashboard.html`

### Test suite

```bash
cd ARC_Console
pytest -q
```

## What makes ARC-Core different

Most “AI agent” repos start with a model and improvise the rest.

ARC-Core starts with:
- state
- schema
- auditability
- replay
- receipts
- bounded execution
- approval lanes
- evidence

That makes it useful for:
- signal intelligence consoles
- deterministic agent infrastructure
- operator dashboards
- case and proposal systems
- geospatial incident tracking
- structured memory backbones
- future synthetic cognition runtimes

## Recommended GitHub description

**Deterministic event, graph, proposal, case, receipt, and geospatial intelligence kernel for the wider ARC / Synth / Lucifer ecosystem.**

## Recommended GitHub topics

`agi, arc, signal-intelligence, cognitive-architecture, deterministic-systems, fastapi, event-sourcing, graph, geospatial, case-management, receipts, system-of-record`

## Roadmap direction

Near-term next steps:
1. unify the split-bundle packaging into a cleaner default checkout experience
2. add explicit event schema docs and end-to-end examples
3. expose richer operator workflows around proposals and evidence review
4. add stronger visuals/screenshots/gifs for public discoverability
5. extend connectors beyond filesystem JSONL
6. deepen branch simulation and rollback semantics
7. connect ARC-Core more directly to ARC-Turbo-OS and Synth runtime surfaces

## Documentation map

- [Architecture overview](docs/ARCHITECTURE.md)
- [Full ecosystem stack](docs/STACK.md)
- [Code-surface audit](docs/CODE_SURFACE_AUDIT.md)
- [SEO and promotion guide](docs/SEO_PROMOTION.md)
- [Repo setup checklist](docs/REPO_SETUP_CHECKLIST.md)

## License

MIT
