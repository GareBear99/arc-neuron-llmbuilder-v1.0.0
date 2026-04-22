
use obi_ir::IrUnit;
use obi_receipts::{Architecture, CompilationPreview, HostProfile};

#[derive(Debug, Clone)]
pub struct CraneliftPlan {
    pub status: &'static str,
    pub next_step: &'static str,
    pub ready_for: Vec<&'static str>,
}

pub fn plan() -> CraneliftPlan {
    CraneliftPlan {
        status: "stub",
        next_step: "wire obi-ir blocks into a baseline compiler and emit host code for a tiny arithmetic proof path",
        ready_for: vec![
            "baseline JIT backend shape",
            "IR block summary integration",
            "future compiled-block cache keys",
        ],
    }
}

pub fn compile_preview(ir: &IrUnit, host: &HostProfile) -> CompilationPreview {
    let summary = ir.summary();
    let helper_calls = ir
        .blocks
        .iter()
        .flat_map(|b| b.instructions.iter())
        .filter(|i| matches!(i.op, obi_ir::IrOp::CallHost { .. }))
        .count();

    CompilationPreview {
        backend: "cranelift-preview".to_string(),
        host_arch: match host.arch {
            Architecture::X86_64 => Architecture::X86_64,
            Architecture::Aarch64 => Architecture::Aarch64,
            Architecture::Riscv64 => Architecture::Riscv64,
            Architecture::X86 => Architecture::X86,
            Architecture::Arm => Architecture::Arm,
            Architecture::Unknown => Architecture::Unknown,
        },
        entry_symbol: format!("obi_entry_{:x}", summary.entry_guest_address),
        block_count: summary.block_count,
        helper_calls,
        uses_syscalls: summary.contains_syscalls,
        cache_key_hint: format!("preview:{}:{}:{}", summary.entry_guest_address, summary.block_count, helper_calls),
        notes: vec![
            "preview only; no executable machine code is emitted in this repo state".to_string(),
            "intended next step: lower one tiny arithmetic block into real Cranelift IR and finalize it into host code".to_string(),
        ],
    }
}
