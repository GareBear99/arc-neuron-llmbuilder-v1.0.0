use std::{fs, path::{Path, PathBuf}};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use arc_rar_common::ArcRarError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuiCommandEnvelope {
    pub protocol_version: u32,
    pub request_id: Uuid,
    pub op: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuiResponseEnvelope {
    pub protocol_version: u32,
    pub request_id: Uuid,
    pub ok: bool,
    pub message: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuiEventEnvelope {
    pub protocol_version: u32,
    pub event_id: Uuid,
    pub request_id: Option<Uuid>,
    pub level: String,
    pub event_type: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuiStatus {
    pub running: bool,
    pub active_archive: Option<String>,
    pub selected: Vec<String>,
    pub autowrap_required: bool,
    pub last_request_id: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InboxMessage {
    pub path: PathBuf,
    pub envelope: GuiCommandEnvelope,
}

pub fn example_open(path: &str) -> GuiCommandEnvelope {
    GuiCommandEnvelope {
        protocol_version: 1,
        request_id: Uuid::new_v4(),
        op: "open_archive".into(),
        payload: serde_json::json!({"archive": path}),
    }
}

pub fn ipc_paths(root: &Path) -> (PathBuf, PathBuf, PathBuf) {
    (
        root.join("gui-inbox"),
        root.join("gui-outbox"),
        root.join("gui-status.json"),
    )
}

pub fn ensure_ipc_dirs(root: &Path) -> Result<(), ArcRarError> {
    let (inbox, outbox, _) = ipc_paths(root);
    fs::create_dir_all(inbox).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    fs::create_dir_all(outbox).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    Ok(())
}

pub fn send_envelope(root: &Path, env: &GuiCommandEnvelope) -> Result<PathBuf, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (inbox, _, _) = ipc_paths(root);
    let path = inbox.join(format!("{}-{}.json", Utc::now().format("%Y%m%dT%H%M%S%.3fZ"), env.request_id));
    fs::write(&path, serde_json::to_vec_pretty(env).map_err(|e| ArcRarError::Ipc(e.to_string()))?)
        .map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    Ok(path)
}

pub fn pull_next_envelope(root: &Path) -> Result<Option<InboxMessage>, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (inbox, _, _) = ipc_paths(root);
    let mut files = vec![];
    for entry in fs::read_dir(&inbox).map_err(|e| ArcRarError::Ipc(e.to_string()))? {
        let entry = entry.map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            files.push(path);
        }
    }
    files.sort();
    if let Some(path) = files.into_iter().next() {
        let raw = fs::read_to_string(&path).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        let env = serde_json::from_str::<GuiCommandEnvelope>(&raw).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        Ok(Some(InboxMessage { path, envelope: env }))
    } else {
        Ok(None)
    }
}

pub fn ack_inbox_message(message: &InboxMessage) -> Result<(), ArcRarError> {
    if message.path.exists() {
        fs::remove_file(&message.path).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    }
    Ok(())
}

pub fn write_response(root: &Path, env: &GuiResponseEnvelope) -> Result<PathBuf, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (_, outbox, _) = ipc_paths(root);
    let path = outbox.join(format!("{}-response-{}.json", Utc::now().format("%Y%m%dT%H%M%S%.3fZ"), env.request_id));
    fs::write(&path, serde_json::to_vec_pretty(env).map_err(|e| ArcRarError::Ipc(e.to_string()))?)
        .map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    Ok(path)
}

pub fn emit_event(root: &Path, env: &GuiEventEnvelope) -> Result<PathBuf, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (_, outbox, _) = ipc_paths(root);
    let path = outbox.join(format!("{}-event-{}.json", Utc::now().format("%Y%m%dT%H%M%S%.3fZ"), env.event_id));
    fs::write(&path, serde_json::to_vec_pretty(env).map_err(|e| ArcRarError::Ipc(e.to_string()))?)
        .map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    Ok(path)
}

pub fn write_status(root: &Path, status: &GuiStatus) -> Result<PathBuf, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (_, _, status_path) = ipc_paths(root);
    fs::write(&status_path, serde_json::to_vec_pretty(status).map_err(|e| ArcRarError::Ipc(e.to_string()))?)
        .map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    Ok(status_path)
}

pub fn read_status(root: &Path) -> Result<GuiStatus, ArcRarError> {
    let (_, _, status_path) = ipc_paths(root);
    if !status_path.exists() {
        return Ok(GuiStatus {
            running: false,
            active_archive: None,
            selected: vec![],
            autowrap_required: true,
            last_request_id: None,
        });
    }
    let raw = fs::read_to_string(status_path).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
    serde_json::from_str(&raw).map_err(|e| ArcRarError::Ipc(e.to_string()))
}

pub fn watch_events(root: &Path) -> Result<Vec<PathBuf>, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (_, outbox, _) = ipc_paths(root);
    let mut files = vec![];
    for entry in fs::read_dir(outbox).map_err(|e| ArcRarError::Ipc(e.to_string()))? {
        let entry = entry.map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        files.push(entry.path());
    }
    files.sort();
    Ok(files)
}

pub fn read_outbox_payloads(root: &Path) -> Result<Vec<serde_json::Value>, ArcRarError> {
    let mut payloads = vec![];
    for path in watch_events(root)? {
        let raw = fs::read_to_string(&path).map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        let value = serde_json::from_str::<serde_json::Value>(&raw).unwrap_or(serde_json::json!({"raw": raw}));
        payloads.push(value);
    }
    Ok(payloads)
}

pub fn cleanup_outbox(root: &Path, keep_latest: usize) -> Result<usize, ArcRarError> {
    ensure_ipc_dirs(root)?;
    let (_, outbox, _) = ipc_paths(root);
    let mut files = vec![];
    for entry in fs::read_dir(&outbox).map_err(|e| ArcRarError::Ipc(e.to_string()))? {
        let entry = entry.map_err(|e| ArcRarError::Ipc(e.to_string()))?;
        files.push(entry.path());
    }
    files.sort();
    let remove_count = files.len().saturating_sub(keep_latest);
    for path in files.into_iter().take(remove_count) {
        let _ = fs::remove_file(path);
    }
    Ok(remove_count)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_file_ipc() {
        let root = std::env::temp_dir().join(format!("arc-rar-ipc-test-{}", Uuid::new_v4()));
        let env = example_open("/tmp/demo.rar");
        let path = send_envelope(&root, &env).unwrap();
        assert!(path.exists());
        let pulled = pull_next_envelope(&root).unwrap().unwrap();
        assert_eq!(pulled.envelope.request_id, env.request_id);
        let resp = GuiResponseEnvelope {
            protocol_version: 1,
            request_id: env.request_id,
            ok: true,
            message: "ok".into(),
            payload: serde_json::json!({"handled": true}),
        };
        write_response(&root, &resp).unwrap();
        let out = read_outbox_payloads(&root).unwrap();
        assert!(!out.is_empty());
        ack_inbox_message(&pulled).unwrap();
        let _ = fs::remove_dir_all(root);
    }
}
