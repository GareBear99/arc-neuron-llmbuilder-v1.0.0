# Next Steps to Actual Production

## Phase 1 — CLI/core productionization
- Validate `cargo build --release` on macOS, Windows, Linux.
- Add archive fixture tests for zip, 7z, tar, tar.gz, rar-read.
- Harden extraction path traversal protections and symlink policies.
- Add precise exit codes and human-readable/non-JSON output modes.
- Confirm backend tool discovery/version handling on each OS.

## Phase 2 — First native ship target
Choose one OS first:
- macOS if daily-driver focus is Mac
- Windows if market focus is Windows

Required deliverables:
- real archive list UI
- extract/create dialogs
- IPC integration
- launch/focus/open-from-CLI
- signed installer/app bundle

## Phase 3 — OS integration
- file associations
- extract-here / open-with handlers
- app launcher registration
- icons, metadata, mime/UTI/registry integration

## Phase 4 — Cross-platform completion
- implement the other two native frontends
- add native IPC transports
- run CI/build/release validation on all targets
- publish support matrix and tested versions
