# ADR 0001: Federated execution lanes

## Status
Accepted

## Decision
OmniBinary uses multiple execution lanes rather than a single universal engine:
- native direct
- native attach
- foreign DBT
- managed portable
- portable IR
- sandboxed partial

## Rationale
This keeps capability claims truthful, permits targeted optimization, and degrades gracefully when a binary exceeds current support.
