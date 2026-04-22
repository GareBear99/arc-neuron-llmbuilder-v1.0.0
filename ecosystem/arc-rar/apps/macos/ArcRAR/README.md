# Arc-RAR macOS shell target

Target stack:
- SwiftUI for primary UI
- AppKit bridges for Finder-style tables, file associations, NSOpenPanel/NSSavePanel nuance, and app lifecycle hooks
- Rust core loaded through FFI or C ABI wrapper

First native milestones:
1. open archive window
2. table view bound to archive entry model
3. extract/create dialogs
4. Finder integration / open-with binding
5. `arc-rar gui` IPC wiring


This folder now also includes starter source files so the native app path is no longer documentation-only. They are still starter implementations and must be built and validated on target OSes.
