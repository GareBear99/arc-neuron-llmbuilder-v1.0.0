# Arc-RAR FFI Bridge

Arc-RAR now includes a starter `arc-rar-ffi` crate so native shells do not have to shell out to the CLI for every action.

## Exported functions
- `arc_rar_version_json()`
- `arc_rar_sniff_format_json(path)`
- `arc_rar_info_json(path)`
- `arc_rar_list_json(path)`
- `arc_rar_extract_json(path, out)`
- `arc_rar_test_json(path)`
- `arc_rar_create_json(output, format, inputs_json)`
- `arc_rar_string_free(ptr)`

All functions return UTF-8 JSON strings allocated by Rust. The caller must release returned pointers with `arc_rar_string_free`.

## Intended use
- macOS: call from Swift through a module map or bridging header
- Windows: call from C# via `DllImport` / PInvoke
- Linux: call from GTK via Rust directly or another FFI consumer

## Current boundary
This bridge is intentionally JSON-first for simplicity and auditability. It is not yet a final stable ABI. For long-lived production ABI, freeze a header, add version negotiation, and add richer streaming progress callbacks.
