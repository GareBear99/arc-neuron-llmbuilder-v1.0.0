# Implemented vs Planned

## Implemented
- Rust workspace structure
- Core archive command surface
- Host-tool backend execution path
- Config bootstrap and path resolution
- Receipts and intent-validation/autowrap schema
- File-based GUI IPC bridge
- GUI daemon once/loop handling
- Packaging/setup templates

## Partial
- Native app bootstraps
- CI/release templates
- Scripts/bootstrap helpers
- Automation layer
- Packaging integration details

## Planned / not yet complete
- Full macOS native frontend
- Full Windows native frontend
- Full Linux native frontend
- Socket/named-pipe IPC transports
- Signed/notarized installers
- Full target-matrix validation
- Full malicious archive and fixture test suite


## Newly tightened in this pass
- custom config root now resolves to root-scoped paths correctly
- receipt session IDs are now stable within a process session
- extraction now rejects archives with obviously unsafe entry paths before invoking host backends
- support matrix and final boundary docs added


## Native bridge progress
- `crates/arc-rar-ffi` now exists as a JSON-first C ABI starter.
- macOS, Windows, and Linux app folders now contain starter source files instead of documentation only.
- These native shells still require target-OS build, integration, and validation before they count as shipped production apps.
