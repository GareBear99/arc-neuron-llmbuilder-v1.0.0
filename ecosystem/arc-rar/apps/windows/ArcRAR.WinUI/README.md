# Arc-RAR Windows shell target

Target stack:
- WinUI 3
- Windows App SDK
- Rust core via C ABI / FFI bridge

First native milestones:
1. archive browser view
2. extract/create flows
3. Explorer file association and context actions
4. startup from `arc-rar gui`
5. background IPC monitor


This folder now also includes starter source files so the native app path is no longer documentation-only. They are still starter implementations and must be built and validated on target OSes.
