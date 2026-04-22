use std::{path::PathBuf, time::Instant};

use arc_rar_common::{
    begin_autowrap, check, optional, required, AppConfig, ArcRarError, ArchiveFormat, IntentCheck,
    IntentValidationReport, OperationReceipt,
};
use arc_rar_core::{
    backend_doctor, create_archive, extract_archive, info_archive, intent_checks_for_archive_path,
    intent_checks_for_create, intent_checks_for_extract, intent_specs_for_archive_op, list_archive,
    test_archive,
};
use arc_rar_ipc::{ack_inbox_message, cleanup_outbox, emit_event, pull_next_envelope, read_outbox_payloads, read_status, send_envelope, watch_events, write_response, write_status, GuiCommandEnvelope, GuiEventEnvelope, GuiResponseEnvelope, GuiStatus};
use clap::{Args, Parser, Subcommand, ValueEnum};
use uuid::Uuid;

#[derive(Parser, Debug)]
#[command(name = "arc-rar")]
#[command(about = "CLI-first archive manager with GUI control plane")]
struct Cli {
    #[arg(long, default_value_t = true)]
    autowrap: bool,
    #[arg(long, default_value_t = true)]
    strict_intents: bool,
    #[arg(long, default_value_t = false)]
    json: bool,
    #[arg(long)]
    config_root: Option<PathBuf>,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    List { archive: String },
    Extract(ExtractArgs),
    Create(CreateArgs),
    Test { archive: String },
    Info { archive: String },
    Config { #[command(subcommand)] command: ConfigCommands },
    Assoc { #[command(subcommand)] command: AssocCommands },
    Backend { #[command(subcommand)] command: BackendCommands },
    Gui { #[command(subcommand)] command: GuiCommands },
    Api { #[command(subcommand)] command: ApiCommands },
    Automation { #[command(subcommand)] command: AutomationCommands },
}

#[derive(Subcommand, Debug)]
enum ConfigCommands { Print, Init }

#[derive(Args, Debug)]
struct ExtractArgs {
    archive: String,
    #[arg(long)]
    out: String,
}

#[derive(Args, Debug)]
struct CreateArgs {
    output: String,
    inputs: Vec<String>,
    #[arg(long, value_enum)]
    format: CreateFormat,
}

#[derive(Clone, Debug, ValueEnum)]
enum CreateFormat { Zip, Tar, TarGz, SevenZ }

#[derive(Subcommand, Debug)]
enum AssocCommands { Install, Remove, Print }

#[derive(Subcommand, Debug)]
enum BackendCommands { Doctor }

#[derive(Subcommand, Debug)]
enum GuiCommands {
    Start { #[arg(long, default_value_t = false)] hidden: bool },
    Open { archive: String },
    Select { entries: Vec<String> },
    Extract { #[arg(long, default_value_t = false)] selected: bool, #[arg(long)] out: String },
    Create { #[arg(long)] output: String, #[arg(long, value_enum)] format: CreateFormat, inputs: Vec<String> },
    Status,
    Focus,
    Ping,
    Watch,
    DaemonOnce,
    DaemonLoop { #[arg(long, default_value_t = 10)] max: usize },
    CleanupOutbox { #[arg(long, default_value_t = 200)] keep_latest: usize },
    Send { envelope_json: String },
    SendFile { path: String },
}

#[derive(Subcommand, Debug)]
enum ApiCommands { Submit { path: String }, Status }

#[derive(Subcommand, Debug)]
enum AutomationCommands {
    Recipe { name: String, #[arg(long)] from: String, #[arg(long)] to: String },
}

fn main() {
    let cli = Cli::parse();
    let config = load_config(cli.config_root.clone());
    let _ = config.ensure_dirs();
    match cli.command {
        Commands::Config { command } => handle_config(command, &config, cli.json),
        Commands::List { archive } => emit("archive", "list", serde_json::json!({"archive": archive}), &cli, &config, intent_specs_for_archive_op("list"), intent_checks_for_archive_path(&archive), || {
            Ok(serde_json::to_value(list_archive(&archive)?).unwrap())
        }),
        Commands::Extract(args) => emit("archive", "extract", serde_json::json!({"archive": args.archive, "out": args.out}), &cli, &config, intent_specs_for_archive_op("extract"), intent_checks_for_extract(&args.archive, &args.out), || {
            Ok(serde_json::to_value(extract_archive(&args.archive, &args.out)?).unwrap())
        }),
        Commands::Create(args) => emit("archive", "create", serde_json::json!({"output": args.output, "inputs": args.inputs, "format": format_to_string(&args.format)}), &cli, &config, intent_specs_for_archive_op("create"), intent_checks_for_create(&args.output, &args.inputs, &map_format(&args.format)), || {
            Ok(serde_json::to_value(create_archive(&args.output, &args.inputs, map_format(&args.format))?).unwrap())
        }),
        Commands::Test { archive } => emit("archive", "test", serde_json::json!({"archive": archive}), &cli, &config, intent_specs_for_archive_op("test"), intent_checks_for_archive_path(&archive), || {
            Ok(serde_json::to_value(test_archive(&archive)?).unwrap())
        }),
        Commands::Info { archive } => emit("archive", "info", serde_json::json!({"archive": archive}), &cli, &config, intent_specs_for_archive_op("info"), intent_checks_for_archive_path(&archive), || {
            Ok(serde_json::to_value(info_archive(&archive)?).unwrap())
        }),
        Commands::Assoc { command } => emit("archive", "assoc", serde_json::json!({"command": format!("{:?}", command)}), &cli, &config, vec![required("assoc_command_known", "An association command must be selected."), optional("native_installer_hooked", "OS packaging/installers should ultimately apply associations.")], vec![check("assoc_command_known", true, "Association subcommand parsed successfully."), check("native_installer_hooked", false, "Packaging templates are present; OS-specific installers still need to wire them.")], || {
            Ok(serde_json::json!({"assoc": format!("{:?}", command), "note": "apply associations through platform-specific packaging manifests and installers"}))
        }),
        Commands::Backend { command: BackendCommands::Doctor } => emit("archive", "backend_doctor", serde_json::json!({}), &cli, &config, vec![required("backend_inventory_requested", "Backend inventory should be reported.")], vec![check("backend_inventory_requested", true, "Backend doctor request accepted.")], || Ok(serde_json::to_value(backend_doctor()).unwrap())),
        Commands::Gui { command } => handle_gui(command, &cli, &config),
        Commands::Api { command } => handle_api(command, &cli, &config),
        Commands::Automation { command: AutomationCommands::Recipe { name, from, to } } => emit("automation", "recipe", serde_json::json!({"name": name, "from": from, "to": to}), &cli, &config, vec![required("recipe_name_present", "An automation recipe name must be supplied."), required("from_present", "A source folder must be supplied."), required("to_present", "A destination folder must be supplied.")], vec![check("recipe_name_present", !name.trim().is_empty(), "Recipe name was evaluated."), check("from_present", !from.trim().is_empty(), "From path was evaluated."), check("to_present", !to.trim().is_empty(), "To path was evaluated.")], || {
            Ok(serde_json::json!({"recipe": arc_rar_automation::recipe_contract(&name, &from, &to), "rendered": arc_rar_automation::render_recipe(&name, &from, &to)}))
        }),
    }
}

fn load_config(config_root: Option<PathBuf>) -> AppConfig {
    let cfg = if let Some(root) = config_root {
        AppConfig::load_from_root(root).unwrap_or_else(|_| AppConfig::default())
    } else {
        AppConfig::load_or_default()
    };
    if let Err(err) = cfg.validate() {
        eprintln!("invalid config: {}", err);
        std::process::exit(2);
    }
    cfg
}

fn handle_config(command: ConfigCommands, config: &AppConfig, json: bool) {
    match command {
        ConfigCommands::Print => print_output(&serde_json::to_value(config).unwrap(), json),
        ConfigCommands::Init => match config.save_default() {
            Ok(path) => print_output(&serde_json::json!({"ok": true, "path": path}), json),
            Err(e) => { eprintln!("failed to write config: {}", e); std::process::exit(1); }
        },
    }
}

fn emit<F>(
    plane: &str,
    op: &str,
    args: serde_json::Value,
    cli: &Cli,
    config: &AppConfig,
    intent_specs: Vec<arc_rar_common::IntentSpec>,
    checks: Vec<IntentCheck>,
    f: F,
) where F: FnOnce() -> Result<serde_json::Value, ArcRarError> {
    let timer = Instant::now();
    let wrap = begin_autowrap(plane, op, args.clone(), intent_specs.clone());
    let validation = IntentValidationReport::new(intent_specs, checks);

    if cli.autowrap && cli.strict_intents && !validation.all_required_intents_met {
        let err = ArcRarError::IntentViolation("required intents not met; action blocked by strict autowrap".into());
        let receipt = OperationReceipt::new(plane, op, args.clone(), false, err.to_string(), timer.elapsed().as_millis() as i64, wrap, validation);
        let _ = receipt.persist_to_dir(&config.receipt_dir);
        print_output(&serde_json::json!({"receipt": receipt, "error": err.to_string(), "error_code": err.code()}), cli.json);
        std::process::exit(2);
    }

    match f() {
        Ok(value) => {
            let receipt = OperationReceipt::new(plane, op, args, validation.all_required_intents_met, if validation.all_required_intents_met { "ok" } else { "action accounted for, but one or more optional/declared intents remain unmet" }, timer.elapsed().as_millis() as i64, wrap, validation);
            let _ = receipt.persist_to_dir(&config.receipt_dir);
            print_output(&serde_json::json!({"receipt": receipt, "result": value}), cli.json);
        }
        Err(err) => {
            let receipt = OperationReceipt::new(plane, op, args, false, err.to_string(), timer.elapsed().as_millis() as i64, wrap, validation);
            let _ = receipt.persist_to_dir(&config.receipt_dir);
            print_output(&serde_json::json!({"receipt": receipt, "error": err.to_string(), "error_code": err.code()}), cli.json);
            std::process::exit(1);
        }
    }
}

fn handle_gui(command: GuiCommands, cli: &Cli, config: &AppConfig) {
    match command {
        GuiCommands::Start { hidden } => emit_gui("start_gui", serde_json::json!({"hidden": hidden}), cli, config, vec![required("gui_start_requested", "A GUI start request must be issued."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("gui_start_requested", true, "GUI start request was parsed."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")]),
        GuiCommands::Open { archive } => emit_gui("open_archive", serde_json::json!({"archive": archive}), cli, config, vec![required("archive_path_present", "A source archive path must be supplied."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("archive_path_present", !archive.trim().is_empty(), "GUI archive path was evaluated."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")]),
        GuiCommands::Select { entries } => emit_gui("select_entries", serde_json::json!({"entries": entries}), cli, config, vec![required("selection_payload_present", "At least one GUI selection entry should be supplied.")], vec![check("selection_payload_present", !entries.is_empty(), "Selection payload was evaluated.")]),
        GuiCommands::Extract { selected, out } => emit_gui("extract", serde_json::json!({"selected": selected, "out": out}), cli, config, vec![required("output_path_present", "An extraction destination must be supplied."), required("ipc_dir_ready", "IPC directory must be ready for command submission."), optional("selection_or_active_archive_known", "The GUI should know what is being extracted.")], vec![check("output_path_present", !out.trim().is_empty(), "GUI extract output path was evaluated."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated."), check("selection_or_active_archive_known", selected, "Starter command records whether --selected was passed.")]),
        GuiCommands::Create { output, format, inputs } => emit_gui("create", serde_json::json!({"output": output, "format": format_to_string(&format), "inputs": inputs}), cli, config, vec![required("output_path_present", "A GUI create output path must be supplied."), required("input_present", "GUI create must receive input items."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("output_path_present", !output.trim().is_empty(), "GUI create output path was evaluated."), check("input_present", !inputs.is_empty(), "GUI create input list was evaluated."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")]),
        GuiCommands::Status => emit("gui", "status", serde_json::json!({}), cli, config, vec![required("gui_status_requested", "GUI status should be reported.")], vec![check("gui_status_requested", true, "GUI status request accepted.")], || Ok(serde_json::to_value(read_status(&config.ipc_dir)?).unwrap())),
        GuiCommands::Focus => emit_gui("focus", serde_json::json!({}), cli, config, vec![required("focus_requested", "GUI focus should be requested."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("focus_requested", true, "GUI focus request accepted."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")]),
        GuiCommands::Ping => emit_gui("ping", serde_json::json!({}), cli, config, vec![required("gui_ping_requested", "GUI ping should be requested."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("gui_ping_requested", true, "GUI ping request accepted."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")]),
        GuiCommands::Watch => emit("gui", "watch", serde_json::json!({}), cli, config, vec![required("watch_requested", "GUI event watch should be requested.")], vec![check("watch_requested", true, "GUI watch request accepted.")], || Ok(serde_json::to_value(read_outbox_payloads(&config.ipc_dir)?).unwrap())),
        GuiCommands::DaemonOnce => emit("gui", "daemon_once", serde_json::json!({}), cli, config, vec![required("ipc_dir_ready", "IPC directory must be available for daemon processing.")], vec![check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")], || Ok(serde_json::to_value(run_gui_daemon_once(&config.ipc_dir)?).unwrap())),
        GuiCommands::DaemonLoop { max } => emit("gui", "daemon_loop", serde_json::json!({"max": max}), cli, config, vec![required("ipc_dir_ready", "IPC directory must be available for daemon processing."), required("loop_limit_present", "A loop iteration limit must be supplied.")], vec![check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated."), check("loop_limit_present", max > 0, "Loop max was evaluated.")], || Ok(serde_json::to_value(run_gui_daemon_loop(&config.ipc_dir, max)?).unwrap())),
        GuiCommands::CleanupOutbox { keep_latest } => emit("gui", "cleanup_outbox", serde_json::json!({"keep_latest": keep_latest}), cli, config, vec![required("ipc_dir_ready", "IPC directory must be available for cleanup.")], vec![check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")], || Ok(serde_json::json!({"removed": cleanup_outbox(&config.ipc_dir, keep_latest)?}))),
        GuiCommands::Send { envelope_json } => emit("gui", "send", serde_json::json!({"raw": envelope_json}), cli, config, vec![required("envelope_present", "A GUI envelope must be supplied."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("envelope_present", !envelope_json.trim().is_empty(), "GUI envelope payload was evaluated."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")], || {
            let parsed = serde_json::from_str::<GuiCommandEnvelope>(&envelope_json).map_err(|e| ArcRarError::Parse(e.to_string()))?;
            let path = send_envelope(&config.ipc_dir, &parsed)?;
            Ok(serde_json::json!({"submitted": true, "path": path, "request_id": parsed.request_id}))
        }),
        GuiCommands::SendFile { path } => emit("gui", "send_file", serde_json::json!({"path": path}), cli, config, vec![required("path_present", "A file path containing a GUI envelope must be supplied."), required("ipc_dir_ready", "IPC directory must be ready for command submission.")], vec![check("path_present", !path.trim().is_empty(), "GUI envelope file path was evaluated."), check("ipc_dir_ready", config.ipc_dir.exists() || std::fs::create_dir_all(&config.ipc_dir).is_ok(), "IPC directory availability was evaluated.")], || {
            let s = std::fs::read_to_string(&path).map_err(|e| ArcRarError::Io(format!("failed to read {}: {}", path, e)))?;
            let parsed = serde_json::from_str::<GuiCommandEnvelope>(&s).map_err(|e| ArcRarError::Parse(e.to_string()))?;
            let out = send_envelope(&config.ipc_dir, &parsed)?;
            Ok(serde_json::json!({"submitted": true, "path": out, "request_id": parsed.request_id}))
        }),
    }
}

fn handle_api(command: ApiCommands, cli: &Cli, config: &AppConfig) {
    match command {
        ApiCommands::Submit { path } => emit("api", "submit", serde_json::json!({"path": path}), cli, config, vec![required("path_present", "An API submission payload path must be supplied.")], vec![check("path_present", !path.trim().is_empty(), "API submission path was evaluated.")], || {
            let s = std::fs::read_to_string(&path).map_err(|e| ArcRarError::Io(format!("failed to read {}: {}", path, e)))?;
            Ok(serde_json::json!({"submitted": true, "payload": serde_json::from_str::<serde_json::Value>(&s).unwrap_or(serde_json::json!({"raw": s})), "request_id": Uuid::new_v4()}))
        }),
        ApiCommands::Status => emit("api", "status", serde_json::json!({}), cli, config, vec![required("api_status_requested", "API queue status should be requested.")], vec![check("api_status_requested", true, "API status request accepted.")], || Ok(serde_json::json!({"api": "starter", "queue_depth": 0, "autowrap_required": true, "ipc_dir": config.ipc_dir}))),
    }
}


fn run_gui_daemon_once(ipc_root: &std::path::Path) -> Result<serde_json::Value, ArcRarError> {
    let mut status = read_status(ipc_root).unwrap_or(GuiStatus { running: false, active_archive: None, selected: vec![], autowrap_required: true, last_request_id: None });
    status.running = true;
    write_status(ipc_root, &status)?;
    if let Some(message) = pull_next_envelope(ipc_root)? {
        let env = &message.envelope;
        let mut response_payload = serde_json::json!({"handled": true, "op": env.op, "request_id": env.request_id});
        match env.op.as_str() {
            "open_archive" => {
                status.active_archive = env.payload.get("archive").and_then(|v| v.as_str()).map(|s| s.to_string());
                status.selected.clear();
                response_payload["active_archive"] = serde_json::json!(status.active_archive);
            }
            "select_entries" => {
                status.selected = env.payload.get("entries").and_then(|v| v.as_array()).map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect()).unwrap_or_default();
                response_payload["selected_count"] = serde_json::json!(status.selected.len());
            }
            "focus" | "ping" | "start_gui" => {}
            "extract" => {
                response_payload["selection_used"] = serde_json::json!(status.selected);
                response_payload["destination"] = env.payload.get("out").cloned().unwrap_or(serde_json::json!(null));
            }
            "create" => {
                response_payload["requested_create"] = env.payload.clone();
            }
            _ => {
                response_payload["note"] = serde_json::json!("daemon handled unknown op generically");
            }
        }
        status.last_request_id = Some(env.request_id);
        write_status(ipc_root, &status)?;
        let response = GuiResponseEnvelope {
            protocol_version: 1,
            request_id: env.request_id,
            ok: true,
            message: format!("handled {}", env.op),
            payload: response_payload.clone(),
        };
        write_response(ipc_root, &response)?;
        emit_event(ipc_root, &GuiEventEnvelope {
            protocol_version: 1,
            event_id: Uuid::new_v4(),
            request_id: Some(env.request_id),
            level: "info".into(),
            event_type: "gui_command_handled".into(),
            payload: serde_json::json!({"op": env.op, "active_archive": status.active_archive, "selected_count": status.selected.len()}),
        })?;
        ack_inbox_message(&message)?;
        Ok(serde_json::json!({"processed": true, "request_id": env.request_id, "status": status, "response": response}))
    } else {
        write_status(ipc_root, &status)?;
        Ok(serde_json::json!({"processed": false, "message": "no pending GUI commands", "status": status}))
    }
}

fn run_gui_daemon_loop(ipc_root: &std::path::Path, max: usize) -> Result<serde_json::Value, ArcRarError> {
    let mut processed = vec![];
    for _ in 0..max {
        let value = run_gui_daemon_once(ipc_root)?;
        let did_process = value.get("processed").and_then(|v| v.as_bool()).unwrap_or(false);
        processed.push(value);
        if !did_process {
            break;
        }
    }
    Ok(serde_json::json!({"iterations": processed.len(), "results": processed}))
}

fn emit_gui(op: &str, payload: serde_json::Value, cli: &Cli, config: &AppConfig, intent_specs: Vec<arc_rar_common::IntentSpec>, checks: Vec<IntentCheck>) {
    emit("gui", op, payload.clone(), cli, config, intent_specs, checks, || {
        let env = build_gui_envelope(op, payload);
        let path = send_envelope(&config.ipc_dir, &env)?;
        Ok(serde_json::json!({"submitted": true, "ipc_path": path, "envelope": env}))
    });
}

fn build_gui_envelope(op: &str, payload: serde_json::Value) -> GuiCommandEnvelope {
    GuiCommandEnvelope { protocol_version: 1, request_id: Uuid::new_v4(), op: op.into(), payload }
}

fn map_format(value: &CreateFormat) -> ArchiveFormat {
    match value { CreateFormat::Zip => ArchiveFormat::Zip, CreateFormat::Tar => ArchiveFormat::Tar, CreateFormat::TarGz => ArchiveFormat::TarGz, CreateFormat::SevenZ => ArchiveFormat::SevenZ }
}

fn format_to_string(value: &CreateFormat) -> &'static str {
    match value { CreateFormat::Zip => "zip", CreateFormat::Tar => "tar", CreateFormat::TarGz => "tar-gz", CreateFormat::SevenZ => "seven-z" }
}

fn print_output(value: &serde_json::Value, json: bool) {
    if json { println!("{}", serde_json::to_string(value).unwrap()); }
    else { println!("{}", serde_json::to_string_pretty(value).unwrap()); }
}
