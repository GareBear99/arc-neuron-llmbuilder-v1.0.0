use thiserror::Error;

#[derive(Debug, Error)]
pub enum ArcRarError {
    #[error("invalid input: {0}")]
    InvalidInput(String),
    #[error("backend unavailable: {0}")]
    BackendUnavailable(String),
    #[error("io error: {0}")]
    Io(String),
    #[error("unsupported format: {0}")]
    UnsupportedFormat(String),
    #[error("ipc error: {0}")]
    Ipc(String),
    #[error("intent violation: {0}")]
    IntentViolation(String),
    #[error("parse error: {0}")]
    Parse(String),
    #[error("security error: {0}")]
    Security(String),
    #[error("internal error: {0}")]
    Internal(String),
}

impl ArcRarError {
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidInput(_) => "INVALID_INPUT",
            Self::BackendUnavailable(_) => "BACKEND_UNAVAILABLE",
            Self::Io(_) => "IO_ERROR",
            Self::UnsupportedFormat(_) => "UNSUPPORTED_FORMAT",
            Self::Ipc(_) => "IPC_ERROR",
            Self::IntentViolation(_) => "INTENT_VIOLATION",
            Self::Parse(_) => "PARSE_ERROR",
            Self::Security(_) => "SECURITY_ERROR",
            Self::Internal(_) => "INTERNAL_ERROR",
        }
    }
}
