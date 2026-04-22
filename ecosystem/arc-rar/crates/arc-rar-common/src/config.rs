use std::{env, fs, path::{Path, PathBuf}};

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub config_version: u32,
    pub default_extract_dir: Option<PathBuf>,
    pub overwrite_policy: OverwritePolicy,
    pub remember_recent: bool,
    pub receipt_dir: PathBuf,
    pub ipc_dir: PathBuf,
    pub state_dir: PathBuf,
    pub recent_limit: usize,
    pub validator: ValidatorConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OverwritePolicy {
    Ask,
    Yes,
    No,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatorConfig {
    pub autowrap_enabled: bool,
    pub strict_mode: bool,
    pub write_receipts: bool,
    pub emit_violation_on_stubbed_backend: bool,
}

impl AppConfig {
    pub fn default_root() -> PathBuf {
        if let Ok(v) = env::var("ARC_RAR_HOME") {
            return PathBuf::from(v);
        }
        if cfg!(target_os = "windows") {
            if let Ok(appdata) = env::var("APPDATA") {
                return PathBuf::from(appdata).join("Arc-RAR");
            }
        }
        if let Ok(xdg) = env::var("XDG_CONFIG_HOME") {
            return PathBuf::from(xdg).join("arc-rar");
        }
        if let Ok(home) = env::var("HOME") {
            return PathBuf::from(home).join(".config").join("arc-rar");
        }
        PathBuf::from(".arc-rar")
    }

    pub fn from_root(root: impl Into<PathBuf>) -> Self {
        let root = root.into();
        Self {
            config_version: 1,
            default_extract_dir: None,
            overwrite_policy: OverwritePolicy::Ask,
            remember_recent: true,
            receipt_dir: root.join("receipts"),
            ipc_dir: root.join("ipc"),
            state_dir: root.join("state"),
            recent_limit: 50,
            validator: ValidatorConfig::default(),
        }
    }

    pub fn default_config_path() -> PathBuf {
        Self::default_root().join("config.json")
    }

    pub fn config_path_for_root(root: impl AsRef<Path>) -> PathBuf {
        root.as_ref().join("config.json")
    }

    pub fn load_or_default() -> Self {
        Self::load_from_root(Self::default_root()).unwrap_or_else(|_| Self::from_root(Self::default_root()))
    }

    pub fn load_from_root(root: impl Into<PathBuf>) -> Result<Self, std::io::Error> {
        let root = root.into();
        let path = Self::config_path_for_root(&root);
        Self::load_from_path(&path, Some(root))
    }

    pub fn load_from_path(path: &Path, fallback_root: Option<PathBuf>) -> Result<Self, std::io::Error> {
        if !path.exists() {
            return Ok(fallback_root.map(Self::from_root).unwrap_or_default());
        }
        let raw = fs::read_to_string(path)?;
        let mut cfg = serde_json::from_str::<Self>(&raw)
            .unwrap_or_else(|_| fallback_root.clone().map(Self::from_root).unwrap_or_default());
        if let Some(root) = fallback_root {
            cfg.apply_root_if_relative(&root);
        }
        Ok(cfg)
    }

    pub fn save_default(&self) -> Result<PathBuf, std::io::Error> {
        let path = Self::default_config_path();
        self.save_to_path(&path)?;
        Ok(path)
    }

    pub fn save_to_path(&self, path: &Path) -> Result<(), std::io::Error> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, serde_json::to_vec_pretty(self)?)
    }

    pub fn ensure_dirs(&self) -> Result<(), std::io::Error> {
        fs::create_dir_all(&self.receipt_dir)?;
        fs::create_dir_all(&self.ipc_dir)?;
        fs::create_dir_all(&self.state_dir)?;
        Ok(())
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.config_version == 0 {
            return Err("config_version must be >= 1".into());
        }
        if self.recent_limit == 0 {
            return Err("recent_limit must be > 0".into());
        }
        Ok(())
    }

    pub fn apply_root_if_relative(&mut self, root: &Path) {
        if self.receipt_dir.as_os_str().is_empty() || self.receipt_dir.is_relative() {
            self.receipt_dir = root.join(&self.receipt_dir);
        }
        if self.ipc_dir.as_os_str().is_empty() || self.ipc_dir.is_relative() {
            self.ipc_dir = root.join(&self.ipc_dir);
        }
        if self.state_dir.as_os_str().is_empty() || self.state_dir.is_relative() {
            self.state_dir = root.join(&self.state_dir);
        }
        if let Some(dir) = &self.default_extract_dir {
            if dir.is_relative() {
                self.default_extract_dir = Some(root.join(dir));
            }
        }
    }
}

impl Default for AppConfig {
    fn default() -> Self {
        Self::from_root(Self::default_root())
    }
}

impl Default for ValidatorConfig {
    fn default() -> Self {
        Self {
            autowrap_enabled: true,
            strict_mode: true,
            write_receipts: true,
            emit_violation_on_stubbed_backend: true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    #[test]
    fn default_has_required_dirs() {
        let cfg = AppConfig::default();
        assert!(cfg.recent_limit > 0);
        assert!(cfg.receipt_dir.ends_with("receipts"));
        assert!(cfg.ipc_dir.ends_with("ipc"));
        assert!(cfg.state_dir.ends_with("state"));
    }

    #[test]
    fn custom_root_is_honored_when_no_file_exists() {
        let root = std::env::temp_dir().join(format!("arc-rar-config-test-{}", Uuid::new_v4()));
        let cfg = AppConfig::load_from_root(&root).unwrap();
        assert_eq!(cfg.receipt_dir, root.join("receipts"));
        assert_eq!(cfg.ipc_dir, root.join("ipc"));
        assert_eq!(cfg.state_dir, root.join("state"));
    }
}
