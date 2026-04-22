# Final What-Remains Boundary

This repo is as far as it can be pushed here without falsely claiming native completion.

## Finished as far as this environment allows
- Rust workspace structure
- CLI command planes
- host-tool archive execution strategy
- autowrap + intent validation doctrine in code
- receipt persistence
- file-based GUI IPC bridge + daemon loop
- packaging/setup/bootstrap documentation
- custom OS / adapter guidance
- stronger config/session/security handling

## Still requires real target-machine work
- compile and test with Cargo on target systems
- implement full macOS native app
- implement full Windows native app
- implement full Linux native app
- sign/notarize/package installers
- validate backend behavior across real target matrices


## Native bridge progress
- `crates/arc-rar-ffi` now exists as a JSON-first C ABI starter.
- macOS, Windows, and Linux app folders now contain starter source files instead of documentation only.
- These native shells still require target-OS build, integration, and validation before they count as shipped production apps.
