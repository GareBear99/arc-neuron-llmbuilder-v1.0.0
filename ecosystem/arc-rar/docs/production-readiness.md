# Production readiness

## What this pack is
A strong handoff and runtime-oriented starter with CLI/core/autowrap/receipt doctrine.

## What still blocks truthful production claims
- native macOS app not fully implemented
- native Windows app not fully implemented
- native Linux app not fully implemented
- no verified compile/test run in this environment
- no signed installers
- no executed cross-OS QA matrix yet

## Production gate checklist
1. cargo check and cargo test pass on macOS, Windows, Linux
2. archive backends verified on all target OSes
3. one native app per OS implemented and manually smoke tested
4. file association install/uninstall flows verified
5. malicious archive tests added and passing
6. signed installers produced
7. upgrade/uninstall paths tested
8. receipts and config migrations validated


## Native bridge progress
- `crates/arc-rar-ffi` now exists as a JSON-first C ABI starter.
- macOS, Windows, and Linux app folders now contain starter source files instead of documentation only.
- These native shells still require target-OS build, integration, and validation before they count as shipped production apps.
