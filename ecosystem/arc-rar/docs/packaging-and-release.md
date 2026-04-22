# Packaging and release

## Current state

This repo includes a production-minded packaging doctrine, but only the CLI/core/IPC layer is implemented here.

## Windows

- Package CLI as `arc-rar.exe`
- Add PATH option in installer
- Register `.zip`, `.7z`, `.rar`, `.tar`, `.tgz` associations optionally
- Register context actions:
  - Extract here
  - Extract to Arc-RAR folder
  - Compress to ZIP
  - Compress to 7z
- Future native UI target: WinUI 3 shell app hosting the same IPC/control plane

## macOS

- Package CLI in `Arc-RAR.app/Contents/MacOS/arc-rar` or install into `/usr/local/bin`/Homebrew cellar
- Register document types for open-with flows
- Future native UI target: SwiftUI/AppKit shell using the same IPC/control plane and receipts

## Linux

- Install CLI to `/usr/bin/arc-rar` or distro package target
- Install `.desktop` file and MIME bindings where desired
- Future native UI target: GTK 4 shell using the same IPC/control plane and receipts

## Release checklist

1. Run unit and integration tests
2. Verify backend doctor on each target OS
3. Verify receipt creation and config bootstrap
4. Verify GUI inbox/outbox file IPC behavior
5. Verify archive list/extract/create/test against real fixtures
6. Verify file associations if enabled
7. Publish support matrix by OS/tool availability
