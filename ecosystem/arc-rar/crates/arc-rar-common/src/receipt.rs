use std::{fs, path::Path, sync::OnceLock};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::intent::{AutowrapContext, IntentValidationReport};

static SESSION_ID: OnceLock<Uuid> = OnceLock::new();

pub fn current_session_id() -> Uuid {
    *SESSION_ID.get_or_init(Uuid::new_v4)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationReceipt {
    pub id: Uuid,
    pub created_at: DateTime<Utc>,
    pub plane: String,
    pub op: String,
    pub args: serde_json::Value,
    pub ok: bool,
    pub message: String,
    pub duration_ms: i64,
    pub session_id: Uuid,
    pub autowrap: AutowrapContext,
    pub validation: IntentValidationReport,
}

impl OperationReceipt {
    pub fn new(
        plane: impl Into<String>,
        op: impl Into<String>,
        args: serde_json::Value,
        ok: bool,
        message: impl Into<String>,
        duration_ms: i64,
        autowrap: AutowrapContext,
        validation: IntentValidationReport,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            created_at: Utc::now(),
            plane: plane.into(),
            op: op.into(),
            args,
            ok,
            message: message.into(),
            duration_ms,
            session_id: current_session_id(),
            autowrap,
            validation,
        }
    }

    pub fn persist_to_dir(&self, dir: &Path) -> Result<std::path::PathBuf, std::io::Error> {
        fs::create_dir_all(dir)?;
        let path = dir.join(format!("{}-{}-{}.json", self.created_at.format("%Y%m%dT%H%M%SZ"), self.plane, self.id));
        fs::write(&path, serde_json::to_vec_pretty(self)?)?;
        Ok(path)
    }
}
