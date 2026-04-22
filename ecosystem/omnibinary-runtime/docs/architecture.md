# Architecture

OmniBinary is organized as a federated execution fabric.

## Core flow
1. Intake parses the input and computes a stable fingerprint.
2. Core detects the host and selects an execution lane.
3. Policy decides whether the launch is allowed.
4. Native or future non-native lane runs the program.
5. Receipts are written to stdout and persisted to local cache.

## Current implemented path
- Intake
- Host detection
- Lane selection
- Policy gate
- Native launch
- Receipt persistence

## Next-step lanes
- Foreign DBT
- Managed portable lane
- Portable IR packaging lane
- Personality-backed syscall mediation
- Brokered sandbox execution


## Repo-state note

The current code implements intake, classification, receipts, cache indexing, and the same-host native proof lane. DBT, managed portable execution, and syscall personalities remain planned but are not runnable yet.
