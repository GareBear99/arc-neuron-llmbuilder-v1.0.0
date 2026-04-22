use obi_receipts::{DecisionReceipt, ExecutionLane, SupportLevel};
use std::path::Path;

pub fn allow_execution(decision: &DecisionReceipt) -> Result<(), String> {
    if !Path::new(&decision.metadata.path).exists() {
        return Err("execution denied: path does not exist".to_string());
    }

    match decision.selected_lane {
        ExecutionLane::Unsupported => Err("execution denied: unsupported lane".to_string()),
        ExecutionLane::ForeignDbt | ExecutionLane::ManagedPortable | ExecutionLane::PortableIr => {
            Err("execution denied: lane selected but not yet implemented in this repo state".to_string())
        }
        ExecutionLane::SandboxedPartial if matches!(decision.support_level, SupportLevel::Unsupported) => {
            Err("execution denied: partial lane selected without a runnable adapter".to_string())
        }
        ExecutionLane::NativeDirect | ExecutionLane::NativeAttach | ExecutionLane::SandboxedPartial => Ok(()),
    }
}

pub fn can_plan(decision: &DecisionReceipt) -> bool {
    !matches!(decision.selected_lane, ExecutionLane::Unsupported)
}
