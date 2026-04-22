use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IntentSeverity {
    Required,
    Optional,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentSpec {
    pub key: String,
    pub description: String,
    pub severity: IntentSeverity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentCheck {
    pub key: String,
    pub met: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViolationRecord {
    pub code: String,
    pub message: String,
    pub violated_intents: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentValidationReport {
    pub all_required_intents_met: bool,
    pub intent_specs: Vec<IntentSpec>,
    pub checks: Vec<IntentCheck>,
    pub violations: Vec<ViolationRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutowrapContext {
    pub wrap_id: Uuid,
    pub created_at: DateTime<Utc>,
    pub plane: String,
    pub op: String,
    pub args: serde_json::Value,
    pub intent_specs: Vec<IntentSpec>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutowrapOutcome<T> {
    pub wrap: AutowrapContext,
    pub validation: IntentValidationReport,
    pub result: Option<T>,
}

impl IntentValidationReport {
    pub fn new(intent_specs: Vec<IntentSpec>, checks: Vec<IntentCheck>) -> Self {
        let required_keys: Vec<String> = intent_specs
            .iter()
            .filter(|s| matches!(s.severity, IntentSeverity::Required))
            .map(|s| s.key.clone())
            .collect();

        let violated_required: Vec<String> = checks
            .iter()
            .filter(|c| !c.met && required_keys.iter().any(|k| k == &c.key))
            .map(|c| c.key.clone())
            .collect();

        let all_required_intents_met = violated_required.is_empty();
        let violations = if all_required_intents_met {
            vec![]
        } else {
            vec![ViolationRecord {
                code: "INTENT_UNMET".into(),
                message: "One or more required intents were not met.".into(),
                violated_intents: violated_required,
            }]
        };

        Self {
            all_required_intents_met,
            intent_specs,
            checks,
            violations,
        }
    }
}

pub fn required(key: impl Into<String>, description: impl Into<String>) -> IntentSpec {
    IntentSpec {
        key: key.into(),
        description: description.into(),
        severity: IntentSeverity::Required,
    }
}

pub fn optional(key: impl Into<String>, description: impl Into<String>) -> IntentSpec {
    IntentSpec {
        key: key.into(),
        description: description.into(),
        severity: IntentSeverity::Optional,
    }
}

pub fn check(key: impl Into<String>, met: bool, detail: impl Into<String>) -> IntentCheck {
    IntentCheck {
        key: key.into(),
        met,
        detail: detail.into(),
    }
}

pub fn begin_autowrap(
    plane: impl Into<String>,
    op: impl Into<String>,
    args: serde_json::Value,
    intent_specs: Vec<IntentSpec>,
) -> AutowrapContext {
    AutowrapContext {
        wrap_id: Uuid::new_v4(),
        created_at: Utc::now(),
        plane: plane.into(),
        op: op.into(),
        args,
        intent_specs,
    }
}
