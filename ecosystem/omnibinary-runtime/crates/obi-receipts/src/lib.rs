
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BinaryFormat {
    Elf,
    Pe,
    MachO,
    Wasm,
    Jar,
    DotNet,
    Script,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Architecture {
    X86_64,
    Aarch64,
    Riscv64,
    X86,
    Arm,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Endianness {
    Little,
    Big,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ExecutionLane {
    NativeDirect,
    NativeAttach,
    ForeignDbt,
    ManagedPortable,
    PortableIr,
    SandboxedPartial,
    Unsupported,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SupportLevel {
    Full,
    Partial,
    Planned,
    Unsupported,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BinaryMetadata {
    pub path: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub format: BinaryFormat,
    pub arch: Architecture,
    pub endianness: Endianness,
    pub os_hint: Option<String>,
    pub word_size_bits: Option<u8>,
    pub is_probably_script: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostProfile {
    pub os: String,
    pub arch: Architecture,
    pub family: String,
    pub endian: Endianness,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub metadata: BinaryMetadata,
    pub host: HostProfile,
    pub selected_lane: ExecutionLane,
    pub support_level: SupportLevel,
    pub reason: String,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub decision: DecisionReceipt,
    pub argv: Vec<String>,
    pub exit_code: Option<i32>,
    pub success: bool,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReceiptIndexEntry {
    pub created_at_utc: DateTime<Utc>,
    pub category: String,
    pub stem: String,
    pub path: String,
    pub sha256: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DoctorReport {
    pub created_at_utc: DateTime<Utc>,
    pub cache_root: String,
    pub host: HostProfile,
    pub checks: Vec<DoctorCheck>,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DoctorCheck {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub decision: DecisionReceipt,
    pub ir_summary: IrSummary,
    pub next_steps: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IrSummary {
    pub entry_guest_address: u64,
    pub block_count: usize,
    pub instruction_count: usize,
    pub contains_calls: bool,
    pub contains_syscalls: bool,
    pub contains_memory_ops: bool,
    pub semantics_notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationBlockSummary {
    pub block_id: usize,
    pub guest_start: u64,
    pub guest_end: u64,
    pub instruction_count: usize,
    pub exit_kind: String,
    pub invalidation_triggers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompilationPreview {
    pub backend: String,
    pub host_arch: Architecture,
    pub entry_symbol: String,
    pub block_count: usize,
    pub helper_calls: usize,
    pub uses_syscalls: bool,
    pub cache_key_hint: String,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DbtExecutionOutline {
    pub lane_status: String,
    pub requires_decoder: bool,
    pub requires_personality: bool,
    pub translation_blocks: Vec<TranslationBlockSummary>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoweringReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub decision: DecisionReceipt,
    pub ir_summary: IrSummary,
    pub dbt_outline: DbtExecutionOutline,
    pub compilation_preview: CompilationPreview,
    pub next_steps: Vec<String>,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToyDecodedInstruction {
    pub offset: u64,
    pub opcode_hex: String,
    pub semantic_hint: String,
    pub lowered_op: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecodeReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub decision: DecisionReceipt,
    pub bytes_examined: usize,
    pub decoder_mode: String,
    pub instructions: Vec<ToyDecodedInstruction>,
    pub ir_summary: IrSummary,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DispatchStep {
    pub step_index: usize,
    pub block_id: usize,
    pub action: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DispatchPreviewReceipt {
    pub created_at_utc: DateTime<Utc>,
    pub decision: DecisionReceipt,
    pub compiled_blocks: Vec<String>,
    pub dispatch_steps: Vec<DispatchStep>,
    pub invalidation_watchpoints: Vec<String>,
    pub notes: Vec<String>,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnvReport {
    pub created_at_utc: DateTime<Utc>,
    pub cwd: String,
    pub cache_root: String,
    pub config_path: String,
    pub host: HostProfile,
    pub important_env: Vec<(String, String)>,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReceiptSummary {
    pub created_at_utc: DateTime<Utc>,
    pub total_entries: usize,
    pub categories: Vec<(String, usize)>,
    pub latest_entries: Vec<ReceiptIndexEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeConfig {
    pub cache_dir: String,
    pub receipt_limit: usize,
    pub strict_policy: bool,
    pub allow_native_direct: bool,
    pub allow_native_attach: bool,
    pub allow_foreign_dbt: bool,
    pub allow_managed_portable: bool,
    pub emit_receipts: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupportInventory {
    pub formats_detected: Vec<String>,
    pub lanes: Vec<String>,
    pub native_execution_available: bool,
    pub dbt_status: String,
    pub managed_status: String,
    pub notes: Vec<String>,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionCoreReport {
    pub created_at_utc: DateTime<Utc>,
    pub decode_contract_ready: bool,
    pub lowering_contract_ready: bool,
    pub cache_contract_ready: bool,
    pub personality_contract_ready: bool,
    pub sandbox_contract_ready: bool,
    pub blockers: Vec<String>,
    pub next_milestones: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixtureManifest {
    pub created_at_utc: DateTime<Utc>,
    pub fixture_root: String,
    pub files: Vec<String>,
    pub notes: Vec<String>,
}



#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheValidationIssue {
    pub level: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheValidationReport {
    pub created_at_utc: DateTime<Utc>,
    pub cache_root: String,
    pub index_entries_checked: usize,
    pub missing_paths: usize,
    pub orphan_receipts: usize,
    pub ok: bool,
    pub issues: Vec<CacheValidationIssue>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionSliceReport {
    pub created_at_utc: DateTime<Utc>,
    pub slices: Vec<String>,
    pub ready_now: Vec<String>,
    pub blocked_by: Vec<String>,
    pub next_cut_line: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MilestoneCheckReport {
    pub created_at_utc: DateTime<Utc>,
    pub status: String,
    pub completed: Vec<String>,
    pub remaining: Vec<String>,
    pub next_actions: Vec<String>,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReadinessCheck {
    pub name: String,
    pub status: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReadinessReport {
    pub created_at_utc: DateTime<Utc>,
    pub profile: String,
    pub checks: Vec<ReadinessCheck>,
    pub release_blocked: bool,
    pub recommended_next_cut: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaneMatrixRow {
    pub lane: String,
    pub implemented_now: bool,
    pub preview_only: bool,
    pub support_level: String,
    pub blockers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaneMatrixReport {
    pub created_at_utc: DateTime<Utc>,
    pub rows: Vec<LaneMatrixRow>,
    pub summary: String,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseBlockersReport {
    pub created_at_utc: DateTime<Utc>,
    pub target: String,
    pub blockers: Vec<String>,
    pub unblock_actions: Vec<String>,
    pub release_ready: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImplementationBacklogReport {
    pub created_at_utc: DateTime<Utc>,
    pub milestone: String,
    pub tracks: Vec<(String, Vec<String>)>,
    pub shortest_path: Vec<String>,
    pub notes: Vec<String>,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreflightReport {
    pub created_at_utc: DateTime<Utc>,
    pub path: String,
    pub selected_lane: String,
    pub support_level: String,
    pub runnable_now: bool,
    pub blockers: Vec<String>,
    pub recommended_commands: Vec<String>,
    pub receipt_categories_expected: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TruthLedgerReport {
    pub created_at_utc: DateTime<Utc>,
    pub claims_safe_now: Vec<String>,
    pub claims_not_safe_now: Vec<String>,
    pub required_for_completion: Vec<String>,
    pub summary: String,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletionMapReport {
    pub created_at_utc: DateTime<Utc>,
    pub target: String,
    pub completed_foundations: Vec<String>,
    pub preview_only_layers: Vec<String>,
    pub missing_runtime_core: Vec<String>,
    pub completion_ratio_hint: String,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidencePackReport {
    pub created_at_utc: DateTime<Utc>,
    pub included_reports: Vec<String>,
    pub cache_root: String,
    pub indexed_receipts: usize,
    pub machine_validated: bool,
    pub release_recommendation: String,
    pub summary: String,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeCoreScoreReport {
    pub created_at_utc: DateTime<Utc>,
    pub target_profile: String,
    pub implemented_slices: Vec<String>,
    pub blocked_slices: Vec<String>,
    pub readiness_score_percent: u8,
    pub next_cut_line: String,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MachineEvidencePlanReport {
    pub created_at_utc: DateTime<Utc>,
    pub required_hosts: Vec<String>,
    pub required_commands: Vec<String>,
    pub expected_outputs: Vec<String>,
    pub archive_targets: Vec<String>,
    pub summary: String,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepoAuditCheck {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepoAuditReport {
    pub created_at_utc: DateTime<Utc>,
    pub repo_root: String,
    pub checks: Vec<RepoAuditCheck>,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportPackReport {
    pub created_at_utc: DateTime<Utc>,
    pub expected_reports: Vec<String>,
    pub present_reports: Vec<String>,
    pub missing_reports: Vec<String>,
    pub indexed_receipts: usize,
    pub cache_root: String,
    pub summary: String,
}
