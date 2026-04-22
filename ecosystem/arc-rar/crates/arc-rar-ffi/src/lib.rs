use std::{ffi::{CStr, CString}, os::raw::c_char, panic};

use arc_rar_common::ArchiveFormat;

fn cstr_to_string(ptr: *const c_char) -> Option<String> {
    if ptr.is_null() {
        return None;
    }
    unsafe { CStr::from_ptr(ptr).to_str().ok().map(|s| s.to_string()) }
}

fn to_c_string(value: String) -> *mut c_char {
    CString::new(value).unwrap_or_else(|_| CString::new("{\"ok\":false,\"error\":\"CString conversion failed\"}").unwrap()).into_raw()
}

fn wrap_json<F>(f: F) -> *mut c_char
where
    F: FnOnce() -> serde_json::Value + panic::UnwindSafe,
{
    let value = match panic::catch_unwind(f) {
        Ok(v) => v,
        Err(_) => serde_json::json!({"ok": false, "error": "panic in FFI call"}),
    };
    to_c_string(serde_json::to_string(&value).unwrap_or_else(|_| "{\"ok\":false,\"error\":\"serialization failure\"}".into()))
}

#[no_mangle]
pub extern "C" fn arc_rar_string_free(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        let _ = CString::from_raw(ptr);
    }
}

#[no_mangle]
pub extern "C" fn arc_rar_version_json() -> *mut c_char {
    wrap_json(|| serde_json::json!({
        "ok": true,
        "name": "Arc-RAR",
        "version": env!("CARGO_PKG_VERSION")
    }))
}

#[no_mangle]
pub extern "C" fn arc_rar_sniff_format_json(path: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let path = cstr_to_string(path).unwrap_or_default();
        let format = arc_rar_core::sniff_format(&path);
        serde_json::json!({"ok": true, "path": path, "format": format})
    })
}

#[no_mangle]
pub extern "C" fn arc_rar_info_json(path: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let path = cstr_to_string(path).unwrap_or_default();
        match arc_rar_core::info_archive(&path) {
            Ok(info) => serde_json::json!({"ok": true, "info": info}),
            Err(err) => serde_json::json!({"ok": false, "code": err.code(), "error": err.to_string()}),
        }
    })
}

#[no_mangle]
pub extern "C" fn arc_rar_list_json(path: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let path = cstr_to_string(path).unwrap_or_default();
        match arc_rar_core::list_archive(&path) {
            Ok(entries) => serde_json::json!({"ok": true, "entries": entries}),
            Err(err) => serde_json::json!({"ok": false, "code": err.code(), "error": err.to_string()}),
        }
    })
}

#[no_mangle]
pub extern "C" fn arc_rar_extract_json(path: *const c_char, out: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let path = cstr_to_string(path).unwrap_or_default();
        let out = cstr_to_string(out).unwrap_or_default();
        match arc_rar_core::extract_archive(&path, &out) {
            Ok(summary) => serde_json::json!({"ok": true, "summary": summary}),
            Err(err) => serde_json::json!({"ok": false, "code": err.code(), "error": err.to_string()}),
        }
    })
}

#[no_mangle]
pub extern "C" fn arc_rar_test_json(path: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let path = cstr_to_string(path).unwrap_or_default();
        match arc_rar_core::test_archive(&path) {
            Ok(summary) => serde_json::json!({"ok": true, "summary": summary}),
            Err(err) => serde_json::json!({"ok": false, "code": err.code(), "error": err.to_string()}),
        }
    })
}

#[no_mangle]
pub extern "C" fn arc_rar_create_json(output: *const c_char, format: *const c_char, inputs_json: *const c_char) -> *mut c_char {
    wrap_json(|| {
        let output = cstr_to_string(output).unwrap_or_default();
        let fmt = cstr_to_string(format).unwrap_or_default();
        let inputs_json = cstr_to_string(inputs_json).unwrap_or_else(|| "[]".into());
        let inputs: Vec<String> = serde_json::from_str(&inputs_json).unwrap_or_default();
        let format = match fmt.as_str() {
            "zip" => ArchiveFormat::Zip,
            "tar" => ArchiveFormat::Tar,
            "tar-gz" | "targz" | "tar.gz" => ArchiveFormat::TarGz,
            "7z" | "seven-z" | "sevenz" => ArchiveFormat::SevenZ,
            _ => ArchiveFormat::Unknown,
        };
        match arc_rar_core::create_archive(&output, &inputs, format) {
            Ok(summary) => serde_json::json!({"ok": true, "summary": summary}),
            Err(err) => serde_json::json!({"ok": false, "code": err.code(), "error": err.to_string()}),
        }
    })
}
