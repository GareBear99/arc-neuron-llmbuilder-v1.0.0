# ARC-Core Architecture Overview

## Core principle

ARC-Core is designed around a simple doctrine:

**models may assist, but canonical state and execution authority stay inside structured infrastructure.**

## Major layers

### 1. API layer
- `arc/api/main.py`
- `arc/api/routes.py`
- `arc/api/deps.py`

Responsibilities:
- application startup
- route exposure
- UI mounting
- manifest/health surface
- auth/session endpoints
- analyst and operator workflow endpoints

### 2. Core layer
- `arc/core/config.py`
- `arc/core/db.py`
- `arc/core/auth.py`
- `arc/core/schemas.py`
- `arc/core/risk.py`
- `arc/core/simulator.py`
- `arc/core/util.py`

Responsibilities:
- config and paths
- SQLite schema and connection bootstrap
- role gates
- typed input/output models
- risk banding
- lightweight simulation primitives
- normalization and event fingerprinting

### 3. Service layer
- `arc/services/ingest.py`
- `arc/services/graph.py`
- `arc/services/cases.py`
- `arc/services/watchlists.py`
- `arc/services/proposals.py`
- `arc/services/notebook.py`
- `arc/services/audit.py`
- `arc/services/authn.py`
- `arc/services/connectors.py`
- `arc/services/bootstrap.py`
- `arc/services/geospatial.py`
- `arc/services/resolver.py`

Responsibilities:
- business logic
- ingest and graph updates
- analyst workflow
- audit/receipt logic
- session logic
- connectors
- geospatial processing
- demo bootstrap and seed data

### 4. Geo layer
- `arc/geo/geometry.py`
- `arc/geo/estimator.py`

Responsibilities:
- polygon / structure geometry helpers
- estimated location and spatial confidence helpers

### 5. UI layer
- `arc/ui/*.html`

Responsibilities:
- dashboard-level views
- graph/timeline/case/geospatial pages

### 6. Tests
- `tests/*.py`

Responsibilities:
- smoke coverage
- workflow coverage
- geospatial coverage
- hardening checks
- v6 operations checks

## Architectural value

This architecture already shows the intended pattern:
- routes stay thin
- services hold workflow logic
- core defines the invariants
- receipts and proposals are explicit
- future model layers can plug in without owning truth
