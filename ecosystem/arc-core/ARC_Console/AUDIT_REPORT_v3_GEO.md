# ARC-Core Audit Report v3 — Geospatial Expansion

This pass integrates the strongest reusable geotracking concepts from the uploaded spatial intelligence package into ARC-Core without pretending to provide real-world covert collection.

## Added
- structure registry with polygon storage
- seeded sensor deployment per structure
- weighted RSSI-style indoor estimate pipeline
- geofence registry and breach detection
- track history persistence
- geo operator page
- demo-track generator for repeatable testing

## Authenticity impact
The repo now feels much closer to a grounded ARC-like operator kernel because it can correlate entities, events, and indoor geospatial estimates in one deterministic surface.

## Remaining gaps
- real connector ingestion
- authenticated device telemetry
- calibrated propagation models
- floorplan image alignment and rich map rendering
- tamper-evident audit chain
- true role/session auth
