use anyhow::{bail, Result};
use chrono::Utc;
use clap::{Parser, Subcommand};
use obi_receipts::{
    CacheValidationReport, CompletionMapReport, DecodeReceipt, DispatchPreviewReceipt, DoctorCheck,
    DoctorReport, EnvReport, EvidencePackReport, ExecutionCoreReport, ExecutionLane,
    ExecutionReceipt, ExecutionSliceReport, FixtureManifest, ImplementationBacklogReport,
    LaneMatrixReport, LaneMatrixRow, LoweringReceipt, MachineEvidencePlanReport,
    MilestoneCheckReport, PlanReceipt, PreflightReport, ReadinessCheck, ReadinessReport,
    ReleaseBlockersReport, RepoAuditCheck, RepoAuditReport, ReportPackReport, RuntimeCoreScoreReport, SupportInventory, TruthLedgerReport,
};
use std::path::PathBuf;
use tracing_subscriber::EnvFilter;

#[derive(Debug, Parser)]
#[command(name = "obi")]
#[command(about = "OmniBinary Runtime CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Debug, Subcommand)]
enum Commands {
    Inspect { path: PathBuf },
    Run {
        path: PathBuf,
        #[arg(trailing_var_arg = true)]
        args: Vec<String>,
    },
    Explain { path: PathBuf },
    Plan { path: PathBuf },
    Lower { path: PathBuf },
    Decode { path: PathBuf },
    Dispatch { path: PathBuf },
    Doctor,
    Receipts {
        #[arg(default_value_t = 20)]
        limit: usize,
    },
    CacheDir,
    CacheStats,
    InitConfig,
    Support,
    Status,
    EnvReport,
    ReceiptSummary,
    ClearCache,
    CoreGap,
    FixtureManifest,
    MilestoneCheck,
    CacheValidate,
    SliceReport,
    ReadinessReport,
    LaneMatrix,
    ReleaseBlockers,
    ImplBacklog,
    Preflight { path: PathBuf },
    TruthLedger,
    CompletionMap,
    EvidencePack,
    RuntimeCoreScore,
    MachineEvidencePlan,
    RepoAudit,
    ReportPack,
}

fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_target(false)
        .compact()
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Inspect { path } => {
            let decision = inspect_decision(&path)?;
            let stem = format!("inspect-{}", decision.metadata.sha256);
            let saved = obi_cache::write_json("inspects", &stem, &decision, Some(&decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&decision)?);
            eprintln!("saved inspect receipt: {}", saved.display());
        }
        Commands::Run { path, args } => {
            let decision = inspect_decision(&path)?;
            obi_policy::allow_execution(&decision).map_err(anyhow::Error::msg)?;
            println!("{}", serde_json::to_string_pretty(&decision)?);
            match decision.selected_lane {
                ExecutionLane::NativeDirect => {
                    let code = obi_lane_native::execute(&path, &args)?;
                    let receipt = ExecutionReceipt {
                        created_at_utc: Utc::now(),
                        decision,
                        argv: args.clone(),
                        exit_code: Some(code),
                        success: code == 0,
                        notes: vec!["native direct lane executed".to_string()],
                    };
                    let stem = format!("run-{}", receipt.decision.metadata.sha256);
                    let saved = obi_cache::write_json("runs", &stem, &receipt, Some(&receipt.decision.metadata.sha256))?;
                    println!("{}", serde_json::to_string_pretty(&receipt)?);
                    eprintln!("saved run receipt: {}", saved.display());
                }
                lane => bail!("selected lane {:?} is not yet implemented in this repo state", lane),
            }
        }
        Commands::Explain { path } => {
            let decision = inspect_decision(&path)?;
            let mut lines = Vec::new();
            lines.push(format!("selected lane: {:?}", decision.selected_lane));
            lines.push(format!("support level: {:?}", decision.support_level));
            lines.push(format!("reason: {}", decision.reason));
            if !decision.blockers.is_empty() {
                lines.push("blockers:".to_string());
                for blocker in &decision.blockers {
                    lines.push(format!("- {}", blocker));
                }
            }
            lines.push(format!("dbt lane status: {:?}", obi_lane_dbt::plan()));
            lines.push(format!("cranelift lane status: {:?}", obi_jit_cranelift::plan()));
            lines.push(format!("llvm lane status: {:?}", obi_jit_llvm::plan()));
            lines.push(format!("managed lane status: {:?}", obi_lane_managed::plan()));
            lines.push(format!("linux personality surface: {:?}", obi_personality_linux::surface()));
            println!("{}", lines.join("\n"));
        }
        Commands::Plan { path } => {
            let decision = inspect_decision(&path)?;
            if !obi_policy::can_plan(&decision) {
                bail!("planning denied: unsupported input shape for current repo state");
            }
            let ir = obi_ir::build_demo_plan(&decision.metadata);
            let receipt = PlanReceipt {
                created_at_utc: Utc::now(),
                decision,
                ir_summary: ir.summary(),
                next_steps: vec![
                    "replace demo lowering with real guest decode".to_string(),
                    "emit baseline machine code through Cranelift".to_string(),
                    "attach invalidation metadata for translated blocks".to_string(),
                    "mediate syscalls through personality layer before runnable foreign execution".to_string(),
                ],
            };
            let stem = format!("plan-{}", receipt.decision.metadata.sha256);
            let saved = obi_cache::write_json("plans", &stem, &receipt, Some(&receipt.decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&receipt)?);
            eprintln!("saved plan receipt: {}", saved.display());
        }
        Commands::Lower { path } => {
            let decision = inspect_decision(&path)?;
            if !obi_policy::can_plan(&decision) {
                bail!("lowering denied: unsupported input shape for current repo state");
            }
            let ir = obi_ir::build_demo_plan(&decision.metadata);
            let dbt_outline = obi_lane_dbt::outline(&ir, &decision.host);
            let compilation_preview = obi_jit_cranelift::compile_preview(&ir, &decision.host);
            let receipt = LoweringReceipt {
                created_at_utc: Utc::now(),
                decision,
                ir_summary: ir.summary(),
                dbt_outline,
                compilation_preview,
                next_steps: vec![
                    "decode one real guest basic block into the canonical IR".to_string(),
                    "lower that block into executable host code".to_string(),
                    "store compiled block metadata in the persistent cache".to_string(),
                    "route syscalls and faults through a real personality adapter".to_string(),
                ],
            };
            let stem = format!("lower-{}", receipt.decision.metadata.sha256);
            let saved = obi_cache::write_json("lowers", &stem, &receipt, Some(&receipt.decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&receipt)?);
            eprintln!("saved lower receipt: {}", saved.display());
        }
        Commands::Decode { path } => {
            let decision = inspect_decision(&path)?;
            let prefix = obi_intake::read_prefix(&path, 16)?;
            let (instructions, ir) = obi_lane_dbt::toy_decode(&prefix, &decision);
            let receipt = DecodeReceipt {
                created_at_utc: Utc::now(),
                decision,
                bytes_examined: prefix.len(),
                decoder_mode: "toy-byte-preview".to_string(),
                instructions,
                ir_summary: ir.summary(),
                notes: vec![
                    "decoder preview only; this is not a real ISA decoder".to_string(),
                    "use this path to validate repo plumbing before implementing a true guest decoder".to_string(),
                ],
            };
            let stem = format!("decode-{}", receipt.decision.metadata.sha256);
            let saved = obi_cache::write_json("decodes", &stem, &receipt, Some(&receipt.decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&receipt)?);
            eprintln!("saved decode receipt: {}", saved.display());
        }
        Commands::Dispatch { path } => {
            let decision = inspect_decision(&path)?;
            let prefix = obi_intake::read_prefix(&path, 16)?;
            let (_instructions, ir) = obi_lane_dbt::toy_decode(&prefix, &decision);
            let receipt = DispatchPreviewReceipt {
                created_at_utc: Utc::now(),
                decision,
                compiled_blocks: ir.translation_blocks().iter().map(|tb| format!("tb:{}:{}", tb.block_id, tb.guest_start)).collect(),
                dispatch_steps: obi_lane_dbt::dispatch_steps(&ir),
                invalidation_watchpoints: obi_lane_dbt::invalidation_watchpoints(&ir),
                notes: vec![
                    "dispatch preview only; no executable foreign code runs here".to_string(),
                    "intended next step is resolve-block -> compile -> execute -> re-enter with a real code cache".to_string(),
                ],
            };
            let stem = format!("dispatch-{}", receipt.decision.metadata.sha256);
            let saved = obi_cache::write_json("dispatch", &stem, &receipt, Some(&receipt.decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&receipt)?);
            eprintln!("saved dispatch receipt: {}", saved.display());
        }
        Commands::Doctor => {
            let host = obi_core::detect_host();
            let cache_root = obi_cache::ensure_layout()?;
            let checks = vec![
                DoctorCheck { name: "host-detected".to_string(), ok: true, detail: format!("host={} arch={:?}", host.os, host.arch) },
                DoctorCheck { name: "cache-layout".to_string(), ok: cache_root.exists(), detail: cache_root.display().to_string() },
                DoctorCheck { name: "native-lane".to_string(), ok: true, detail: "same-ISA native direct launch path is implemented".to_string() },
                DoctorCheck { name: "plan-lane".to_string(), ok: true, detail: "IR demo planning path is implemented".to_string() },
                DoctorCheck { name: "lower-preview".to_string(), ok: true, detail: "DBT outline + compilation preview receipt path is implemented".to_string() },
                DoctorCheck { name: "toy-decoder".to_string(), ok: true, detail: "toy decode preview path is implemented for byte-to-IR plumbing".to_string() },
                DoctorCheck { name: "dispatch-preview".to_string(), ok: true, detail: "translation-block dispatch preview path is implemented".to_string() },
                DoctorCheck { name: "config-scaffold".to_string(), ok: true, detail: "runtime config init path is implemented".to_string() },
                DoctorCheck { name: "dbt-lane".to_string(), ok: false, detail: "planned only; no foreign-ISA execution backend yet".to_string() },
                DoctorCheck { name: "managed-lane".to_string(), ok: false, detail: "planned only; no wasm/jar/.NET execution backend yet".to_string() },
                DoctorCheck { name: "compile-status".to_string(), ok: false, detail: "not compile-checked in this packaging environment because cargo is unavailable".to_string() },
            ];
            let report = DoctorReport {
                created_at_utc: Utc::now(),
                cache_root: cache_root.display().to_string(),
                host,
                summary: "repo scaffold is useful and structured, but not production-ready".to_string(),
                checks,
            };
            let saved = obi_cache::write_json("doctor", "latest", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved doctor report: {}", saved.display());
        }
        Commands::Receipts { limit } => {
            let entries = obi_cache::read_index(limit)?;
            println!("{}", serde_json::to_string_pretty(&entries)?);
        }
        Commands::CacheDir => {
            let dir = obi_cache::ensure_layout()?;
            println!("{}", dir.display());
        }
        Commands::CacheStats => {
            let stats = obi_cache::stats()?;
            println!("{}", serde_json::to_string_pretty(&stats)?);
        }
        Commands::InitConfig => {
            let path = obi_config::init_config_file()?;
            println!("{}", path.display());
        }
        Commands::EnvReport => {
            let host = obi_core::detect_host();
            let cache_root = obi_cache::ensure_layout()?;
            let cwd = std::env::current_dir()?.display().to_string();
            let config_path = obi_config::config_path().display().to_string();
            let important_env = ["OBI_CACHE_DIR", "OBI_CONFIG", "HOME", "LOCALAPPDATA", "USER", "USERNAME"]
                .iter()
                .filter_map(|key| std::env::var(key).ok().map(|value| ((*key).to_string(), value)))
                .collect();
            let report = EnvReport {
                created_at_utc: Utc::now(),
                cwd,
                cache_root: cache_root.display().to_string(),
                config_path,
                host,
                important_env,
                notes: vec![
                    "environment report is intended for deterministic support/debug triage".to_string(),
                    "sensitive secrets should not be placed in environment variables before sharing reports".to_string(),
                ],
            };
            let saved = obi_cache::write_json("env", "latest", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved env report: {}", saved.display());
        }
        Commands::ReceiptSummary => {
            let summary = obi_cache::summarize_index(10)?;
            println!("{}", serde_json::to_string_pretty(&summary)?);
        }
        Commands::ClearCache => {
            let removed = obi_cache::clear_generated_receipts()?;
            println!("{}", serde_json::to_string_pretty(&removed)?);
        }
        Commands::CoreGap => {
            let report = ExecutionCoreReport {
                created_at_utc: Utc::now(),
                decode_contract_ready: true,
                lowering_contract_ready: true,
                cache_contract_ready: true,
                personality_contract_ready: true,
                sandbox_contract_ready: true,
                blockers: vec![
                    "no real guest ISA decoder is implemented yet".to_string(),
                    "no runnable Cranelift-emitted translated host block exists yet".to_string(),
                    "no syscall personality mediation exists yet".to_string(),
                    "no brokered sandbox execution plane exists yet".to_string(),
                    "the repo has not been compile-validated in this packaging environment".to_string(),
                ],
                next_milestones: vec![
                    "implement one real guest decoder for aarch64 basic blocks".to_string(),
                    "lower decoded guest ops into canonical IR values and control flow".to_string(),
                    "emit one runnable host block through Cranelift and return through a re-entry stub".to_string(),
                    "persist translated block metadata and invalidation reasons in cache".to_string(),
                    "mediate at least one Linux userspace syscall surface through the personality layer".to_string(),
                    "execute translated code inside a brokered process boundary with deterministic receipts".to_string(),
                ],
            };
            let saved = obi_cache::write_json("core-gap", "latest", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved core gap report: {}", saved.display());
        }
        Commands::FixtureManifest => {
            let fixture_root = PathBuf::from("tests/fixtures");
            let mut files = Vec::new();
            if fixture_root.exists() {
                fn walk(dir: &std::path::Path, files: &mut Vec<String>) -> anyhow::Result<()> {
                    for entry in std::fs::read_dir(dir)? {
                        let entry = entry?;
                        let path = entry.path();
                        let ty = entry.file_type()?;
                        if ty.is_dir() {
                            walk(&path, files)?;
                        } else if ty.is_file() {
                            files.push(path.display().to_string());
                        }
                    }
                    Ok(())
                }
                walk(&fixture_root, &mut files)?;
                files.sort();
            }
            let manifest = FixtureManifest {
                created_at_utc: Utc::now(),
                fixture_root: fixture_root.display().to_string(),
                files,
                notes: vec![
                    "fixture manifest is a repository-level inventory only".to_string(),
                    "real execution fixtures should be licensed, reproducible, and architecture-tagged".to_string(),
                ],
            };
            let saved = obi_cache::write_json("fixtures", "latest", &manifest, None)?;
            println!("{}", serde_json::to_string_pretty(&manifest)?);
            eprintln!("saved fixture manifest: {}", saved.display());
        }
        Commands::MilestoneCheck => {
            let report = MilestoneCheckReport {
                created_at_utc: Utc::now(),
                status: "scaffold-strong-core-missing".to_string(),
                completed: vec![
                    "binary intake and format heuristics".to_string(),
                    "lane selection and native-direct proof path".to_string(),
                    "IR planning, lowering preview, toy decode, and dispatch preview".to_string(),
                    "cache/index/config/docs/release-track scaffolding".to_string(),
                ],
                remaining: vec![
                    "real guest decoder".to_string(),
                    "real lowering to canonical executable form".to_string(),
                    "real Cranelift-emitted runnable translated block".to_string(),
                    "translated block cache invalidation".to_string(),
                    "personality mediation and brokered sandbox".to_string(),
                ],
                next_actions: vec![
                    "implement one aarch64 basic-block smoke decoder".to_string(),
                    "emit one host block with Cranelift and a re-entry stub".to_string(),
                    "validate cache/index hygiene after translated block writes".to_string(),
                ],
            };
            let saved = obi_cache::write_json("reports", "milestone-check", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved milestone report: {}", saved.display());
        }
        Commands::CacheValidate => {
            let report: CacheValidationReport = obi_cache::validate_index()?;
            let saved = obi_cache::write_json("reports", "cache-validate", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved cache validation report: {}", saved.display());
        }
        Commands::SliceReport => {
            let report = ExecutionSliceReport {
                created_at_utc: Utc::now(),
                slices: vec![
                    "slice-1: intake -> inspect -> native direct".to_string(),
                    "slice-2: toy decode -> canonical IR preview".to_string(),
                    "slice-3: real aarch64 basic-block decode".to_string(),
                    "slice-4: Cranelift emission for one translated block".to_string(),
                    "slice-5: cache reuse + invalidation + brokered execution".to_string(),
                ],
                ready_now: vec![
                    "slice-1".to_string(),
                    "slice-2".to_string(),
                ],
                blocked_by: vec![
                    "no real guest decoder implementation in repo".to_string(),
                    "no compile validation in packaging environment".to_string(),
                    "no sandbox/personality backend yet".to_string(),
                ],
                next_cut_line: "finish slice-3 plus one runnable Cranelift-emitted block to cross from scaffold into real translation runtime".to_string(),
            };
            let saved = obi_cache::write_json("reports", "slice-report", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved slice report: {}", saved.display());
        }
        Commands::ReadinessReport => {
            let report = ReadinessReport {
                created_at_utc: Utc::now(),
                profile: "production-universal-runtime".to_string(),
                checks: vec![
                    ReadinessCheck { name: "repo-governance".to_string(), status: "ready".to_string(), detail: "license, CI scaffolding, templates, scripts, and docs exist".to_string() },
                    ReadinessCheck { name: "native-direct-lane".to_string(), status: "ready".to_string(), detail: "same-ISA native execution proof path exists".to_string() },
                    ReadinessCheck { name: "dbt-preview-lane".to_string(), status: "partial".to_string(), detail: "planning, lowering preview, toy decode, and dispatch preview exist".to_string() },
                    ReadinessCheck { name: "foreign-isa-execution".to_string(), status: "blocked".to_string(), detail: "no real guest decoder or runnable translated block exists yet".to_string() },
                    ReadinessCheck { name: "personality-layer".to_string(), status: "blocked".to_string(), detail: "no syscall mediation backend is implemented yet".to_string() },
                    ReadinessCheck { name: "sandbox-broker".to_string(), status: "blocked".to_string(), detail: "no brokered execution plane exists yet".to_string() },
                    ReadinessCheck { name: "machine-validation".to_string(), status: "blocked".to_string(), detail: "repo not compile-validated in this packaging environment".to_string() },
                ],
                release_blocked: true,
                recommended_next_cut: "implement one real guest basic-block decoder plus one Cranelift-emitted runnable translated host block".to_string(),
            };
            let saved = obi_cache::write_json("reports", "readiness-report", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved readiness report: {}", saved.display());
        }
        Commands::LaneMatrix => {
            let report = LaneMatrixReport {
                created_at_utc: Utc::now(),
                rows: vec![
                    LaneMatrixRow { lane: "NativeDirect".to_string(), implemented_now: true, preview_only: false, support_level: "usable".to_string(), blockers: vec![] },
                    LaneMatrixRow { lane: "NativeAttach".to_string(), implemented_now: false, preview_only: true, support_level: "planned".to_string(), blockers: vec!["no attach/rewriter backend".to_string()] },
                    LaneMatrixRow { lane: "ForeignDbt".to_string(), implemented_now: false, preview_only: true, support_level: "preview".to_string(), blockers: vec!["no real decoder".to_string(), "no runnable translated blocks".to_string()] },
                    LaneMatrixRow { lane: "ManagedPortable".to_string(), implemented_now: false, preview_only: true, support_level: "planned".to_string(), blockers: vec!["no wasm/jvm/.net execution backend".to_string()] },
                    LaneMatrixRow { lane: "PortableIr".to_string(), implemented_now: false, preview_only: true, support_level: "doctrine-only".to_string(), blockers: vec!["no import/repackage pipeline".to_string()] },
                    LaneMatrixRow { lane: "SandboxedPartial".to_string(), implemented_now: false, preview_only: true, support_level: "planned".to_string(), blockers: vec!["no brokered sandbox plane".to_string()] },
                ],
                summary: "repo is strong on intake, receipts, and execution planning; only NativeDirect is runnable in the current package".to_string(),
            };
            let saved = obi_cache::write_json("reports", "lane-matrix", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved lane matrix report: {}", saved.display());
        }

        Commands::ReleaseBlockers => {
            let report = ReleaseBlockersReport {
                created_at_utc: Utc::now(),
                target: "production-universal-runtime".to_string(),
                blockers: vec![
                    "foreign-ISA translated execution backend is still missing".to_string(),
                    "no real guest ISA decoder exists in the repo".to_string(),
                    "no runnable Cranelift-emitted translated host block exists yet".to_string(),
                    "no syscall personality mediation backend exists yet".to_string(),
                    "no brokered sandbox execution plane exists yet".to_string(),
                    "no supported-machine compile/test evidence is bundled with this package".to_string(),
                ],
                unblock_actions: vec![
                    "implement one aarch64 basic-block smoke decoder".to_string(),
                    "lower decoded guest ops into canonical IR and emit one host block".to_string(),
                    "execute that block through a tiny re-entry loop and persist cache metadata".to_string(),
                    "mediate at least one Linux userspace syscall surface".to_string(),
                    "run the repo on a supported machine and archive cargo check/test results".to_string(),
                ],
                release_ready: false,
            };
            let saved = obi_cache::write_json("reports", "release-blockers", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved release blockers report: {}", saved.display());
        }
        Commands::ImplBacklog => {
            let report = ImplementationBacklogReport {
                created_at_utc: Utc::now(),
                milestone: "first-real-translation-milestone".to_string(),
                tracks: vec![
                    ("decoder".to_string(), vec!["aarch64 basic-block smoke decoder".to_string(), "register + flags mapping".to_string(), "branch target extraction".to_string()]),
                    ("lowering".to_string(), vec!["map decoded ops into canonical IR".to_string(), "preserve memory-op semantics".to_string(), "define guest-to-host helper ABI".to_string()]),
                    ("emission".to_string(), vec!["emit one host block through Cranelift".to_string(), "create entry/re-entry stub".to_string(), "record helper and cache metadata".to_string()]),
                    ("runtime".to_string(), vec!["dispatch one translated block".to_string(), "store invalidation watchpoints".to_string(), "surface deterministic crash receipts".to_string()]),
                    ("validation".to_string(), vec!["cargo check/test on supported machine".to_string(), "fixture-based smoke test".to_string(), "cache/index validation after translated writes".to_string()]),
                ],
                shortest_path: vec![
                    "decode one real guest block".to_string(),
                    "lower it into canonical IR".to_string(),
                    "emit one runnable host block".to_string(),
                    "re-enter through a tiny dispatch loop".to_string(),
                    "prove it with one fixture and one machine-validated test run".to_string(),
                ],
                notes: vec![
                    "this backlog is the cut line between a strong scaffold and a true translation runtime".to_string(),
                    "until these steps exist, the repo should not be described as complete".to_string(),
                ],
            };
            let saved = obi_cache::write_json("reports", "impl-backlog", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved implementation backlog report: {}", saved.display());
        }

        Commands::Preflight { path } => {
            let decision = inspect_decision(&path)?;
            let runnable_now = matches!(decision.selected_lane, ExecutionLane::NativeDirect) && decision.blockers.is_empty();
            let report = PreflightReport {
                created_at_utc: Utc::now(),
                path: path.display().to_string(),
                selected_lane: format!("{:?}", decision.selected_lane),
                support_level: format!("{:?}", decision.support_level),
                runnable_now,
                blockers: decision.blockers.clone(),
                recommended_commands: vec![
                    format!("obi inspect {}", path.display()),
                    format!("obi explain {}", path.display()),
                    format!("obi plan {}", path.display()),
                    format!("obi lower {}", path.display()),
                ],
                receipt_categories_expected: vec![
                    "inspects".to_string(),
                    "plans".to_string(),
                    "lowers".to_string(),
                    "decodes".to_string(),
                    "dispatch".to_string(),
                    "runs".to_string(),
                ],
            };
            let stem = format!("preflight-{}", decision.metadata.sha256);
            let saved = obi_cache::write_json("reports", &stem, &report, Some(&decision.metadata.sha256))?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved preflight report: {}", saved.display());
        }
        Commands::TruthLedger => {
            let report = TruthLedgerReport {
                created_at_utc: Utc::now(),
                claims_safe_now: vec![
                    "repo is a strong execution-fabric scaffold".to_string(),
                    "same-ISA native-direct proof path exists".to_string(),
                    "intake, receipts, cache, config, and planning surfaces exist".to_string(),
                    "toy decode and dispatch preview paths exist for plumbing validation".to_string(),
                ],
                claims_not_safe_now: vec![
                    "complete universal runtime".to_string(),
                    "real foreign-ISA execution backend".to_string(),
                    "runnable Cranelift-translated guest blocks".to_string(),
                    "full syscall personality mediation".to_string(),
                    "production-ready sandbox broker plane".to_string(),
                    "compile/test validated in this packaging environment".to_string(),
                ],
                required_for_completion: vec![
                    "one real guest ISA decoder".to_string(),
                    "one real canonical lowering path".to_string(),
                    "one real Cranelift-emitted runnable translated block".to_string(),
                    "translated block cache reuse and invalidation".to_string(),
                    "one real syscall personality surface".to_string(),
                    "brokered sandbox execution plane".to_string(),
                    "supported-machine compile/test validation evidence".to_string(),
                ],
                summary: "truth ledger separates what this repo can honestly claim now from what still requires runtime-core implementation work".to_string(),
            };
            let saved = obi_cache::write_json("reports", "truth-ledger", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved truth ledger report: {}", saved.display());
        }

        Commands::CompletionMap => {
            let report = CompletionMapReport {
                created_at_utc: Utc::now(),
                target: "production-universal-runtime".to_string(),
                completed_foundations: vec![
                    "repo governance and release scaffolding".to_string(),
                    "binary intake and lane selection".to_string(),
                    "native-direct proof execution path".to_string(),
                    "receipt/cache/config/reporting surfaces".to_string(),
                ],
                preview_only_layers: vec![
                    "dbt planning and lowering preview".to_string(),
                    "toy decode and dispatch preview".to_string(),
                    "managed and portable lane doctrines".to_string(),
                ],
                missing_runtime_core: vec![
                    "real guest ISA decoder".to_string(),
                    "real canonical lowering".to_string(),
                    "runnable Cranelift-emitted translated blocks".to_string(),
                    "translated block cache reuse and invalidation".to_string(),
                    "syscall personality mediation".to_string(),
                    "sandbox/broker execution plane".to_string(),
                    "machine-validated compile/test evidence".to_string(),
                ],
                completion_ratio_hint: "repo/package foundation is strong; runtime-core completion remains materially unfinished".to_string(),
                summary: "completion map separates finished foundations from preview-only layers and the remaining runtime-core work required for a truthful completion claim".to_string(),
            };
            let saved = obi_cache::write_json("reports", "completion-map", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved completion map: {}", saved.display());
        }
        Commands::EvidencePack => {
            let cache_root = obi_cache::ensure_layout()?;
            let indexed = obi_cache::read_index(usize::MAX)?.len();
            let report = EvidencePackReport {
                created_at_utc: Utc::now(),
                included_reports: vec![
                    "doctor".to_string(),
                    "status".to_string(),
                    "readiness-report".to_string(),
                    "lane-matrix".to_string(),
                    "release-blockers".to_string(),
                    "impl-backlog".to_string(),
                    "truth-ledger".to_string(),
                    "completion-map".to_string(),
                ],
                cache_root: cache_root.display().to_string(),
                indexed_receipts: indexed,
                machine_validated: false,
                release_recommendation: "do not label production ready until one real translated execution path and machine validation evidence exist".to_string(),
                summary: "evidence pack summarizes the current handoff and makes the release boundary explicit for maintainers or auditors".to_string(),
            };
            let saved = obi_cache::write_json("reports", "evidence-pack", &report, None)?;
            println!("{}", serde_json::to_string_pretty(&report)?);
            eprintln!("saved evidence pack: {}", saved.display());
        }

        Commands::Status => {
            let host = obi_core::detect_host();
            let cache_root = obi_cache::ensure_layout()?;
            let stats = obi_cache::stats()?;
            let lines = vec![
                "omnibinary runtime status".to_string(),
                format!("version: {}", env!("CARGO_PKG_VERSION")),
                format!("host: {} {:?}", host.os, host.arch),
                format!("cache: {}", cache_root.display()),
                format!("indexed receipts: {}", stats.total_receipts_indexed),
                "implemented: intake, lane selection, native execution, planning, lowering preview, toy decode, dispatch preview, cache, config, doctor, support inventory, env report, receipt summary".to_string(),
                "execution-core handoff: decode/lowering/cache/personality/sandbox contract docs and core-gap reporting are now included".to_string(),
                "missing for first real translation milestone: one real guest decoder, canonical block lowering, Cranelift-emitted runnable host block, translated block cache metadata, re-entry dispatch loop".to_string(),
                "missing for production readiness: syscall personality mediation, sandbox/broker process model, CI compile/test validation on supported toolchains, fuzzing, release signing, compatibility test matrix".to_string(),
                "truth boundary: this repo is a strong execution-fabric scaffold, not yet a production universal runtime".to_string(),
            ];
            println!("{}", lines.join("\n"));
        }
        Commands::Support => {
            let inv = SupportInventory {
                formats_detected: vec!["ELF".to_string(), "PE".to_string(), "Mach-O".to_string(), "WASM".to_string(), "JAR (heuristic)".to_string(), ".NET (heuristic)".to_string(), "Script (shebang heuristic)".to_string()],
                lanes: vec!["NativeDirect".to_string(), "NativeAttach (planned)".to_string(), "ForeignDbt (planned-with-preview)".to_string(), "ManagedPortable (planned)".to_string(), "PortableIr (planned doctrine)".to_string(), "SandboxedPartial (planned doctrine)".to_string()],
                native_execution_available: true,
                dbt_status: obi_lane_dbt::plan().status.to_string(),
                managed_status: obi_lane_managed::plan().status.to_string(),
                notes: vec![
                    "support inventory is declarative; it does not prove backend completeness".to_string(),
                    "foreign execution remains unavailable until a real decoder + JIT path exists".to_string(),
                ],
            };
            println!("{}", serde_json::to_string_pretty(&inv)?);
        }
    }

    Ok(())
}

fn inspect_decision(path: &PathBuf) -> Result<obi_receipts::DecisionReceipt> {
    let metadata = obi_loader::inspect(path)?;
    Ok(obi_core::choose_lane(metadata))
}
