# Custom OS / Nonstandard Platform Porting Guide

This document is for developers adapting Arc-RAR to a custom operating system, a stripped-down appliance OS, a kiosk build, a game-console-style shell, or another nonstandard environment.

## Minimum explicit information needed from the OS team

A custom OS porter must answer these questions before integration begins:

1. **Process model**
   - Can Arc-RAR spawn child processes?
   - Are background services/daemons allowed?
   - Are pipes, sockets, or shared temp files available?

2. **Filesystem model**
   - Is there a writable user config directory?
   - Are symlinks supported?
   - Are long paths or UTF-8 paths fully supported?
   - Are executable bits or ACLs meaningful?

3. **Windowing/UI model**
   - Native toolkit name and version
   - Main-thread requirements
   - File picker availability
   - Drag-and-drop support
   - Notifications/progress UX hooks

4. **Shell integration model**
   - How are file associations registered?
   - How are context-menu entries registered?
   - Is there an app manifest format?
   - Can CLI commands launch/focus an existing GUI instance?

5. **Archive backend availability**
   - Does the OS ship `tar`?
   - Does it ship `zip/unzip`?
   - Is `7z` / `7zz` / `p7zip` available?
   - Is `unrar` or `libarchive` available?

6. **Security model**
   - Can apps access arbitrary user paths?
   - Are sandbox entitlements needed?
   - Are signed binaries required?
   - Are temporary directories private or shared?

7. **Packaging/distribution model**
   - Native package format
   - install prefix rules
   - shared library lookup rules
   - service registration rules

## Required Arc-RAR integration contracts for a custom OS

A custom OS integration must provide:

- a config root resolver
- a receipt/log root resolver
- an IPC transport resolver
- a file-association installer
- an app-launch bridge for `arc-rar gui`
- an optional context-menu bridge
- a backend capability detector

## Custom OS adapter interface (conceptual)

```text
CustomOsAdapter
  resolve_paths()
  install_file_associations()
  uninstall_file_associations()
  launch_gui(args)
  focus_gui()
  create_ipc_endpoint()
  discover_backends()
  install_shortcuts()
```

## Symlink policy

If the OS supports symlinks:
- provide a stable `arc-rar` binary symlink in a common user or system path
- prefer a versioned install directory + stable symlink pattern

If symlinks are not supported:
- provide a launcher shim or manifest alias

## Path doctrine

Do not hardcode `/usr/local/bin` or platform-specific roots in the core. Route all path decisions through the OS adapter or packaging layer.
