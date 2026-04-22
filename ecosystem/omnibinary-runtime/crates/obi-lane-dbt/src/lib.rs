
use obi_ir::{BasicBlock, IrInstruction, IrOp, IrUnit};
use obi_receipts::{
    DbtExecutionOutline, DecisionReceipt, DispatchStep, IrSummary, ToyDecodedInstruction,
    TranslationBlockSummary, HostProfile,
};

#[derive(Debug, Clone)]
pub struct DbtPlan {
    pub status: &'static str,
    pub next_step: &'static str,
    pub risks: Vec<&'static str>,
    pub toy_decoder_available: bool,
}

pub fn plan() -> DbtPlan {
    DbtPlan {
        status: "stub-plus-preview",
        next_step: "replace toy byte decoder with a real guest ISA decoder, then wire block dispatch into the baseline JIT path",
        risks: vec![
            "self-modifying code invalidation not implemented",
            "syscall personality mediation not implemented",
            "exception and signal mapping not implemented",
        ],
        toy_decoder_available: true,
    }
}

pub fn outline(ir: &IrUnit, host: &HostProfile) -> DbtExecutionOutline {
    let mut notes = vec![
        format!("host target for baseline codegen: {:?}", host.arch),
        "translation-block outlines are derived from demo IR or toy-decoded guest bytes, not a production decoder".to_string(),
        "all outlined blocks require runtime invalidation metadata before execution".to_string(),
    ];
    if ir.summary().contains_syscalls {
        notes.push("syscall-bearing blocks must route through a personality adapter".to_string());
    }

    DbtExecutionOutline {
        lane_status: "planned-with-preview".to_string(),
        requires_decoder: true,
        requires_personality: ir.summary().contains_syscalls,
        translation_blocks: ir.translation_blocks(),
        notes,
    }
}

pub fn toy_decode(bytes: &[u8], decision: &DecisionReceipt) -> (Vec<ToyDecodedInstruction>, IrUnit) {
    let entry = 0x2000;
    let mut instructions = Vec::new();
    let mut ir_instructions = Vec::new();
    let mut saw_syscall = false;

    for (idx, byte) in bytes.iter().take(8).enumerate() {
        let guest_address = entry + (idx as u64) * 4;
        let (semantic_hint, lowered_op, ir_op) = match byte % 7 {
            0 => ("load-like", "Load(8)", IrOp::Load { bytes: 8 }),
            1 => ("const-like", "ConstI64", IrOp::ConstI64(*byte as i64)),
            2 => ("add-like", "Add", IrOp::Add),
            3 => ("sub-like", "Sub", IrOp::Sub),
            4 => ("store-like", "Store(8)", IrOp::Store { bytes: 8 }),
            5 => {
                saw_syscall = true;
                ("syscall-like", "Syscall", IrOp::Syscall { number: *byte as u64 })
            }
            _ => ("host-helper-like", "CallHost(decoder.helper)", IrOp::CallHost { symbol: "decoder.helper".to_string() }),
        };

        instructions.push(ToyDecodedInstruction {
            offset: idx as u64,
            opcode_hex: format!("0x{:02x}", byte),
            semantic_hint: semantic_hint.to_string(),
            lowered_op: lowered_op.to_string(),
        });
        ir_instructions.push(IrInstruction {
            guest_address,
            op: ir_op,
            comment: format!("toy decode from {} byte {}", decision.metadata.path, idx),
        });
    }

    let exit_addr = entry + (ir_instructions.len() as u64) * 4;
    ir_instructions.push(IrInstruction {
        guest_address: exit_addr,
        op: if saw_syscall {
            IrOp::Return
        } else {
            IrOp::Jump { target_block: 1 }
        },
        comment: "toy decoder block terminator".to_string(),
    });

    let block0 = BasicBlock {
        id: 0,
        guest_address: entry,
        instructions: ir_instructions,
    };

    let block1 = BasicBlock {
        id: 1,
        guest_address: entry + 0x80,
        instructions: vec![
            IrInstruction {
                guest_address: entry + 0x80,
                op: IrOp::CallHost { symbol: "dispatch.resume".to_string() },
                comment: "placeholder dispatcher re-entry".to_string(),
            },
            IrInstruction {
                guest_address: entry + 0x84,
                op: IrOp::Return,
                comment: "finish toy-dispatch route".to_string(),
            },
        ],
    };

    (
        instructions,
        IrUnit {
            entry_guest_address: entry,
            blocks: vec![block0, block1],
        },
    )
}

pub fn dispatch_steps(ir: &IrUnit) -> Vec<DispatchStep> {
    let mut steps = Vec::new();
    for (index, block) in ir.blocks.iter().enumerate() {
        steps.push(DispatchStep {
            step_index: index,
            block_id: block.id,
            action: "resolve-block".to_string(),
            detail: format!("resolve guest block at 0x{:x}", block.guest_address),
        });
        steps.push(DispatchStep {
            step_index: index + 100,
            block_id: block.id,
            action: "execute-preview".to_string(),
            detail: format!("execute {} lowered ops in preview mode", block.instructions.len()),
        });
    }
    steps
}

pub fn invalidation_watchpoints(ir: &IrUnit) -> Vec<String> {
    let mut points = vec!["binary hash drift".to_string(), "decoder version drift".to_string()];
    let summary: IrSummary = ir.summary();
    if summary.contains_memory_ops {
        points.push("writes into translated pages".to_string());
    }
    if summary.contains_syscalls {
        points.push("personality adapter contract change".to_string());
    }
    points
}
