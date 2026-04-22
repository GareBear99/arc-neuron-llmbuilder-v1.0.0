# Architecture

Arc-RAR is split into five layers:

1. **Common layer**
   - shared types
   - config
   - receipts
   - stable error model

2. **Core layer**
   - archive format sniffing
   - backend selection
   - list/extract/create/test/info operations
   - backend capability map

3. **CLI layer**
   - archive command plane
   - GUI control plane
   - API/automation plane
   - stdout JSON receipts

4. **IPC layer**
   - terminal -> GUI envelopes
   - status/watch stream
   - background automation control

5. **Native frontend layer**
   - macOS SwiftUI/AppKit
   - Windows WinUI 3
   - Linux GTK 4

## Core principle

Every GUI action must map to:
- a CLI command, or
- an IPC envelope, or
- both.

This guarantees that a person or AI can drive Arc-RAR without touching the GUI directly.


## Validation spine

All command planes now route through a shared **autowrap + intent validation** doctrine. See `docs/autowrap-intent-validation.md`.
