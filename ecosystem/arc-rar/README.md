# Arc-RAR

Arc-RAR is a CLI-first archive manager with a native-app control plane, autowrap intent validation, receipts, and a file-based GUI bridge that works across macOS, Windows, Linux, and custom systems.

## Current truth

This repo is strongest today as:
- a real Rust workspace starter
- a host-tool-backed archive CLI
- a file-based GUI control bridge
- an autowrap + intent-validation spine
- a native-app handoff and packaging kit

It is **not yet an honestly complete production app suite** because the full native SwiftUI, WinUI 3, and GTK frontends still need end-to-end implementation and validation on target systems.

## What works now

- list archives through host tools where available
- inspect archive info
- extract archives through host tools where available
- create zip / tar / tar.gz / 7z through host tools where available
- test archives
- write receipts to disk
- validate intents and emit violations in strict mode
- submit GUI commands into IPC inbox files
- run a file-based GUI daemon loop that consumes GUI commands, updates status, and emits response/event files

## Example flows

### Archive plane

```bash
arc-rar list demo.zip
arc-rar extract demo.zip --out ./out
arc-rar create build.tar.gz ./folder --format tar-gz
arc-rar info demo.rar
arc-rar test demo.7z
```

### GUI control plane

```bash
arc-rar gui open ./demo.rar
arc-rar gui daemon-once
arc-rar gui status
arc-rar gui watch --json
```

### Batch the GUI bridge

```bash
arc-rar gui open ./demo.zip
arc-rar gui select docs/readme.txt src/main.rs
arc-rar gui extract --selected --out ./out
arc-rar gui daemon-loop --max 20
arc-rar gui watch --json
```

## Native target doctrine

- macOS: SwiftUI + AppKit bridge
- Windows: WinUI 3
- Linux: GTK 4
- Shared core: Rust
- Shared command/control spine: Rust CLI + IPC + receipts + autowrap

## Repo status guide

- Implemented: core CLI/archive host-tool path, receipts, config resolution, file IPC, daemon bridge
- Partial: packaging templates, setup scripts, native app bootstraps, tests
- Planned: fully working native GUIs, socket/named-pipe IPC, signed installers, target-matrix validation

## Production reality check

This repository is **not yet production-ready** as a full native app suite. The CLI/core path is the strongest part. The remaining blockers are:
- native macOS frontend implementation and validation
- native Windows frontend implementation and validation
- native Linux frontend implementation and validation
- signed/distributed installers verified on target systems
- real CI/build/test execution across target OSes

Use this repo today as a strong engineering base and handoff, not as a final shipped desktop product.


## Additional docs

- `docs/support-matrix.md`
- `docs/final-what-remains.md`


## New native integration layer
- `crates/arc-rar-ffi` provides a JSON-based C ABI starter for native frontends.
- `docs/ffi-bridge.md` documents the current bridge surface and caller contract.
