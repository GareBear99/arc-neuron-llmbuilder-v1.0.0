use anyhow::Result;
use obi_receipts::RuntimeConfig;
use std::fs;
use std::path::{Path, PathBuf};

pub fn default_config() -> RuntimeConfig {
    RuntimeConfig {
        cache_dir: "~/.cache/omnibinary".to_string(),
        receipt_limit: 50,
        strict_policy: true,
        allow_native_direct: true,
        allow_native_attach: true,
        allow_foreign_dbt: false,
        allow_managed_portable: false,
        emit_receipts: true,
    }
}

pub fn config_path() -> PathBuf {
    if let Ok(path) = std::env::var("OBI_CONFIG") { return PathBuf::from(path); }
    if Path::new("obi.toml").exists() { return PathBuf::from("obi.toml"); }
    if let Ok(home) = std::env::var("HOME") {
        return Path::new(&home).join(".config").join("omnibinary").join("obi.toml");
    }
    PathBuf::from("obi.toml")
}

pub fn init_config_file() -> Result<PathBuf> {
    let path = config_path();
    if let Some(parent) = path.parent() { fs::create_dir_all(parent)?; }
    let c = default_config();
    let body = format!(
        "cache_dir = "{}"
receipt_limit = {}
strict_policy = {}
allow_native_direct = {}
allow_native_attach = {}
allow_foreign_dbt = {}
allow_managed_portable = {}
emit_receipts = {}
",
        c.cache_dir, c.receipt_limit, c.strict_policy, c.allow_native_direct, c.allow_native_attach, c.allow_foreign_dbt, c.allow_managed_portable, c.emit_receipts
    );
    fs::write(&path, body)?;
    Ok(path)
}
