# Arc-RAR Linux shell target

Target stack:
- GTK 4
- GLib main loop for IPC integration
- Rust core directly or via FFI boundary

First native milestones:
1. archive table view
2. extract/create dialogs
3. `.desktop` entry + MIME association
4. `arc-rar gui` IPC bridge
5. distro-specific packaging


This folder now also includes starter source files so the native app path is no longer documentation-only. They are still starter implementations and must be built and validated on target OSes.
