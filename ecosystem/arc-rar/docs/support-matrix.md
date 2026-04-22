# Arc-RAR Support Matrix

## Currently strongest
- CLI/core on macOS, Linux, Windows where host tools are present
- File-based GUI bridge on all systems with filesystem access
- Autowrap + intent validation + receipts

## Archive operations
| Format | List | Info | Test | Extract | Create |
|---|---|---|---|---|---|
| ZIP | Yes via `unzip`/`7z`/`bsdtar` | Yes | Yes | Yes | Yes via `zip`/`7z` |
| TAR | Yes via `tar`/`bsdtar` | Yes | Yes | Yes | Yes |
| TAR.GZ | Yes via `tar`/`bsdtar` | Yes | Yes | Yes | Yes |
| 7Z | Yes via `7z`/`7zz` | Yes | Yes | Yes | Yes |
| RAR | Yes via `unrar`/`7z`/`bsdtar` | Yes | Yes | Yes | No |

## Native GUI status
| OS | Status |
|---|---|
| macOS | placeholder native shell + packaging templates |
| Windows | docs/templates only |
| Linux | placeholder native shell + packaging templates |

## Honest caveats
- Host-tool behavior varies by OS and installed backend versions.
- RAR creation is intentionally unsupported.
- Native GUI apps are not yet complete production implementations.


## Native bridge progress
- `crates/arc-rar-ffi` now exists as a JSON-first C ABI starter.
- macOS, Windows, and Linux app folders now contain starter source files instead of documentation only.
- These native shells still require target-OS build, integration, and validation before they count as shipped production apps.
