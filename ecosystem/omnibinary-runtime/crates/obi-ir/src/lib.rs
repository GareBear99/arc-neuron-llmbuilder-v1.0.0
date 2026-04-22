
use obi_receipts::{BinaryMetadata, IrSummary, TranslationBlockSummary};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValueType {
    I32,
    I64,
    F32,
    F64,
    Ptr,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IrOp {
    ConstI64(i64),
    Load { bytes: u8 },
    Store { bytes: u8 },
    Add,
    Sub,
    Mul,
    Div,
    CompareEq,
    Branch { then_block: usize, else_block: usize },
    Jump { target_block: usize },
    CallHost { symbol: String },
    Syscall { number: u64 },
    Return,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IrInstruction {
    pub guest_address: u64,
    pub op: IrOp,
    pub comment: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BasicBlock {
    pub id: usize,
    pub guest_address: u64,
    pub instructions: Vec<IrInstruction>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IrUnit {
    pub entry_guest_address: u64,
    pub blocks: Vec<BasicBlock>,
}

impl IrUnit {
    pub fn summary(&self) -> IrSummary {
        let mut instruction_count = 0usize;
        let mut contains_calls = false;
        let mut contains_syscalls = false;
        let mut contains_memory_ops = false;
        let mut semantics_notes = vec![
            "lowering plan only; this is not decoded guest code yet".to_string(),
            "intended next step is guest decoder -> canonical IR -> baseline JIT".to_string(),
        ];

        for block in &self.blocks {
            instruction_count += block.instructions.len();
            for instr in &block.instructions {
                match &instr.op {
                    IrOp::CallHost { .. } => contains_calls = true,
                    IrOp::Syscall { .. } => contains_syscalls = true,
                    IrOp::Load { .. } | IrOp::Store { .. } => contains_memory_ops = true,
                    _ => {}
                }
            }
        }

        if contains_memory_ops {
            semantics_notes.push("memory operations require alias, bounds, and page-permission policy in later tiers".to_string());
        }
        if contains_syscalls {
            semantics_notes.push("syscalls require personality mediation before runnable execution".to_string());
        }

        IrSummary {
            entry_guest_address: self.entry_guest_address,
            block_count: self.blocks.len(),
            instruction_count,
            contains_calls,
            contains_syscalls,
            contains_memory_ops,
            semantics_notes,
        }
    }

    pub fn translation_blocks(&self) -> Vec<TranslationBlockSummary> {
        self.blocks
            .iter()
            .map(|block| {
                let guest_end = block
                    .instructions
                    .last()
                    .map(|i| i.guest_address)
                    .unwrap_or(block.guest_address);
                let exit_kind = match block.instructions.last().map(|i| &i.op) {
                    Some(IrOp::Branch { .. }) => "branch",
                    Some(IrOp::Jump { .. }) => "jump",
                    Some(IrOp::Return) => "return",
                    Some(IrOp::Syscall { .. }) => "syscall-boundary",
                    _ => "fallthrough",
                }
                .to_string();

                let mut invalidation_triggers = vec!["binary hash drift".to_string()];
                if block.instructions.iter().any(|i| matches!(i.op, IrOp::Store { .. })) {
                    invalidation_triggers.push("write-into-translated-page".to_string());
                }
                if block.instructions.iter().any(|i| matches!(i.op, IrOp::Syscall { .. })) {
                    invalidation_triggers.push("personality-contract-change".to_string());
                }

                TranslationBlockSummary {
                    block_id: block.id,
                    guest_start: block.guest_address,
                    guest_end,
                    instruction_count: block.instructions.len(),
                    exit_kind,
                    invalidation_triggers,
                }
            })
            .collect()
    }
}

pub fn build_demo_plan(metadata: &BinaryMetadata) -> IrUnit {
    let entry = 0x1000;
    let mut block0 = BasicBlock {
        id: 0,
        guest_address: entry,
        instructions: vec![
            IrInstruction {
                guest_address: entry,
                op: IrOp::Load { bytes: 8 },
                comment: format!("model loader read for {}", metadata.path),
            },
            IrInstruction {
                guest_address: entry + 4,
                op: IrOp::ConstI64(metadata.size_bytes as i64),
                comment: "materialize input size for planning metadata".to_string(),
            },
            IrInstruction {
                guest_address: entry + 8,
                op: IrOp::CompareEq,
                comment: "placeholder branch condition for tier routing".to_string(),
            },
            IrInstruction {
                guest_address: entry + 12,
                op: IrOp::Branch {
                    then_block: 1,
                    else_block: 2,
                },
                comment: "branch to native or mediated path".to_string(),
            },
        ],
    };

    let native = BasicBlock {
        id: 1,
        guest_address: entry + 0x40,
        instructions: vec![
            IrInstruction {
                guest_address: entry + 0x40,
                op: IrOp::CallHost {
                    symbol: "native.exec".to_string(),
                },
                comment: "native-direct or native-attach launch surface".to_string(),
            },
            IrInstruction {
                guest_address: entry + 0x44,
                op: IrOp::Return,
                comment: "finish native route".to_string(),
            },
        ],
    };

    let mediated = BasicBlock {
        id: 2,
        guest_address: entry + 0x80,
        instructions: vec![
            IrInstruction {
                guest_address: entry + 0x80,
                op: IrOp::Load { bytes: 8 },
                comment: "fetch guest state block".to_string(),
            },
            IrInstruction {
                guest_address: entry + 0x84,
                op: IrOp::Syscall { number: 0 },
                comment: "placeholder mediated syscall boundary".to_string(),
            },
            IrInstruction {
                guest_address: entry + 0x88,
                op: IrOp::Return,
                comment: "finish mediated route".to_string(),
            },
        ],
    };

    block0.instructions.shrink_to_fit();

    IrUnit {
        entry_guest_address: entry,
        blocks: vec![block0, native, mediated],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use obi_receipts::{Architecture, BinaryFormat, BinaryMetadata, Endianness};

    #[test]
    fn demo_plan_has_blocks_and_summary() {
        let metadata = BinaryMetadata {
            path: "/bin/echo".to_string(),
            sha256: "abc".to_string(),
            size_bytes: 123,
            format: BinaryFormat::Elf,
            arch: Architecture::X86_64,
            endianness: Endianness::Little,
            os_hint: Some("linux/elf".to_string()),
            word_size_bits: Some(64),
            is_probably_script: false,
        };
        let ir = build_demo_plan(&metadata);
        let summary = ir.summary();
        let tb = ir.translation_blocks();
        assert_eq!(summary.block_count, 3);
        assert!(summary.instruction_count >= 3);
        assert_eq!(tb.len(), 3);
    }
}
