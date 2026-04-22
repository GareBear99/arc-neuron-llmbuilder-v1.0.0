use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ArchiveFormat {
    Zip,
    Tar,
    TarGz,
    SevenZ,
    Rar,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArchiveEntry {
    pub path: String,
    pub size: Option<u64>,
    pub packed_size: Option<u64>,
    pub modified: Option<String>,
    pub is_dir: bool,
    pub encrypted: bool,
    pub method: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArchiveInfo {
    pub path: String,
    pub format: ArchiveFormat,
    pub entries: usize,
    pub encrypted: bool,
    pub backend_used: String,
    pub detected_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationSummary {
    pub ok: bool,
    pub message: String,
    pub output_path: Option<String>,
    pub accounted_for: bool,
    pub intent_contract_satisfied: bool,
    pub backend_used: Option<String>,
}
