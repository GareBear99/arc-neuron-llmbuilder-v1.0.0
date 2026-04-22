use chrono::Utc;
use obi_receipts::{Architecture, BinaryFormat, DecisionReceipt, Endianness, ExecutionLane, HostProfile, SupportLevel};

pub fn detect_host() -> HostProfile {
    let arch = match std::env::consts::ARCH {
        "x86_64" => Architecture::X86_64,
        "aarch64" => Architecture::Aarch64,
        "riscv64" => Architecture::Riscv64,
        "x86" | "i686" => Architecture::X86,
        "arm" => Architecture::Arm,
        _ => Architecture::Unknown,
    };

    let endian = if cfg!(target_endian = "little") {
        Endianness::Little
    } else {
        Endianness::Big
    };

    HostProfile {
        os: std::env::consts::OS.to_string(),
        arch,
        family: std::env::consts::FAMILY.to_string(),
        endian,
    }
}

pub fn choose_lane(metadata: obi_receipts::BinaryMetadata, host: HostProfile) -> DecisionReceipt {
    let mut blockers = Vec::new();
    let (selected_lane, support_level, reason) = if metadata.is_probably_script {
        blockers.push("script execution is not yet routed through an interpreter lane".to_string());
        (
            ExecutionLane::SandboxedPartial,
            SupportLevel::Partial,
            "script-like input detected; runtime can classify it but does not yet broker interpreter execution".to_string(),
        )
    } else if metadata.arch == host.arch {
        match metadata.format {
            BinaryFormat::Elf | BinaryFormat::Pe | BinaryFormat::MachO => (
                ExecutionLane::NativeDirect,
                SupportLevel::Full,
                "guest architecture matches host architecture".to_string(),
            ),
            BinaryFormat::Wasm | BinaryFormat::Jar | BinaryFormat::DotNet => {
                blockers.push("managed portable lane is not yet implemented".to_string());
                (
                    ExecutionLane::ManagedPortable,
                    SupportLevel::Planned,
                    "portable or managed format detected".to_string(),
                )
            }
            _ => {
                blockers.push("format is not recognized as a native or managed artifact".to_string());
                (
                    ExecutionLane::SandboxedPartial,
                    SupportLevel::Partial,
                    "unknown same-architecture input routed to partial lane".to_string(),
                )
            }
        }
    } else {
        match metadata.format {
            BinaryFormat::Elf | BinaryFormat::Pe | BinaryFormat::MachO => {
                blockers.push("foreign-ISA DBT lane is planned but not implemented in this repo state".to_string());
                (
                    ExecutionLane::ForeignDbt,
                    SupportLevel::Planned,
                    "guest architecture differs from host; route to dynamic binary translation lane".to_string(),
                )
            }
            BinaryFormat::Wasm | BinaryFormat::Jar | BinaryFormat::DotNet => {
                blockers.push("managed portable lane is not yet implemented".to_string());
                (
                    ExecutionLane::ManagedPortable,
                    SupportLevel::Planned,
                    "portable or managed format detected".to_string(),
                )
            }
            _ => {
                blockers.push("no compatible execution lane exists for this input in the current repo state".to_string());
                (
                    ExecutionLane::Unsupported,
                    SupportLevel::Unsupported,
                    "format unsupported for direct or DBT launch".to_string(),
                )
            }
        }
    };

    DecisionReceipt {
        created_at_utc: Utc::now(),
        metadata,
        host,
        selected_lane,
        support_level,
        reason,
        blockers,
    }
}
