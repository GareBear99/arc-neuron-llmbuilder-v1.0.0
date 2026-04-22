use std::{
    fs,
    io::Read,
    path::{Path, PathBuf},
    process::Command,
};

use arc_rar_common::{
    check, optional, required, ArcRarError, ArchiveEntry, ArchiveFormat, ArchiveInfo, IntentCheck,
    IntentSpec, OperationSummary,
};
use which::which;

#[derive(Debug, Clone)]
pub struct BackendTool {
    pub label: &'static str,
    pub cmd: &'static str,
}

#[derive(Debug, Default, serde::Serialize)]
pub struct BackendDoctor {
    pub detected_tools: Vec<String>,
    pub missing_tools: Vec<String>,
    pub advice: Vec<String>,
}

const SEVENZ_TOOLS: &[BackendTool] = &[
    BackendTool { label: "7z", cmd: "7z" },
    BackendTool { label: "7zz", cmd: "7zz" },
];

const TAR_TOOLS: &[BackendTool] = &[
    BackendTool { label: "bsdtar", cmd: "bsdtar" },
    BackendTool { label: "tar", cmd: "tar" },
];

const ZIP_TOOLS: &[BackendTool] = &[
    BackendTool { label: "zip", cmd: "zip" },
    BackendTool { label: "unzip", cmd: "unzip" },
];

const RAR_TOOLS: &[BackendTool] = &[
    BackendTool { label: "unrar", cmd: "unrar" },
    BackendTool { label: "rar", cmd: "rar" },
];

fn detect_first(tools: &[BackendTool]) -> Option<&'static str> {
    tools.iter().find_map(|t| which(t.cmd).ok().map(|_| t.cmd))
}

fn command_exists(cmd: &str) -> bool {
    which(cmd).is_ok()
}

fn run_command(cmd: &str, args: &[&str]) -> Result<std::process::Output, ArcRarError> {
    Command::new(cmd)
        .args(args)
        .output()
        .map_err(|e| ArcRarError::BackendUnavailable(format!("failed to launch {}: {}", cmd, e)))
}

pub fn sniff_format(path: &str) -> ArchiveFormat {
    let p = Path::new(path);
    if p.exists() {
        if let Ok(mut f) = fs::File::open(p) {
            let mut header = [0u8; 8];
            if let Ok(n) = f.read(&mut header) {
                let sig = &header[..n];
                if sig.starts_with(&[0x50, 0x4B, 0x03, 0x04]) { return ArchiveFormat::Zip; }
                if sig.starts_with(&[0x52, 0x61, 0x72, 0x21, 0x1A, 0x07]) { return ArchiveFormat::Rar; }
                if sig.starts_with(&[0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C]) { return ArchiveFormat::SevenZ; }
                if sig.starts_with(&[0x1F, 0x8B]) { return ArchiveFormat::TarGz; }
            }
        }
    }
    let lower = path.to_ascii_lowercase();
    if lower.ends_with(".tar.gz") || lower.ends_with(".tgz") {
        ArchiveFormat::TarGz
    } else if lower.ends_with(".tar") {
        ArchiveFormat::Tar
    } else if lower.ends_with(".zip") {
        ArchiveFormat::Zip
    } else if lower.ends_with(".7z") {
        ArchiveFormat::SevenZ
    } else if lower.ends_with(".rar") {
        ArchiveFormat::Rar
    } else {
        ArchiveFormat::Unknown
    }
}

pub fn intent_specs_for_archive_op(op: &str) -> Vec<IntentSpec> {
    match op {
        "list" => vec![
            required("archive_path_present", "A source archive path must be supplied."),
            required("archive_exists", "The source archive path must exist."),
            required("format_supported", "The source archive format must be recognized."),
            optional("backend_available", "A live backend should enumerate real entries."),
        ],
        "info" => vec![
            required("archive_path_present", "A source archive path must be supplied."),
            required("archive_exists", "The source archive path must exist."),
            required("format_supported", "The source archive format must be recognized."),
        ],
        "extract" => vec![
            required("archive_path_present", "A source archive path must be supplied."),
            required("archive_exists", "The source archive path must exist."),
            required("output_path_present", "An extraction destination must be supplied."),
            required("format_supported", "The source archive format must be recognized."),
            optional("backend_available", "A live backend should perform actual extraction."),
        ],
        "create" => vec![
            required("output_path_present", "An archive output path must be supplied."),
            required("input_present", "At least one input path must be supplied."),
            required("inputs_exist", "All provided inputs should exist."),
            required("write_format_supported", "The requested output format must be writable by Arc-RAR."),
            optional("backend_available", "A live backend should create the archive."),
        ],
        "test" => vec![
            required("archive_path_present", "A source archive path must be supplied."),
            required("archive_exists", "The source archive path must exist."),
            required("format_supported", "The source archive format must be recognized."),
            optional("backend_available", "A live backend should validate archive integrity."),
        ],
        _ => vec![required("op_known", "The operation must resolve to a known archive verb.")],
    }
}

fn backend_available(format: &ArchiveFormat, write: bool) -> bool {
    match (format, write) {
        (ArchiveFormat::Zip, false) => command_exists("unzip") || detect_first(SEVENZ_TOOLS).is_some() || detect_first(TAR_TOOLS).is_some(),
        (ArchiveFormat::Zip, true) => command_exists("zip") || detect_first(SEVENZ_TOOLS).is_some(),
        (ArchiveFormat::Tar, false) | (ArchiveFormat::TarGz, false) => detect_first(TAR_TOOLS).is_some(),
        (ArchiveFormat::Tar, true) | (ArchiveFormat::TarGz, true) => detect_first(TAR_TOOLS).is_some(),
        (ArchiveFormat::SevenZ, false) | (ArchiveFormat::SevenZ, true) => detect_first(SEVENZ_TOOLS).is_some(),
        (ArchiveFormat::Rar, false) => command_exists("unrar") || detect_first(SEVENZ_TOOLS).is_some() || command_exists("bsdtar"),
        (ArchiveFormat::Rar, true) => false,
        (ArchiveFormat::Unknown, _) => false,
    }
}

pub fn intent_checks_for_archive_path(path: &str) -> Vec<IntentCheck> {
    let format = sniff_format(path);
    vec![
        check("archive_path_present", !path.trim().is_empty(), "Archive path argument was evaluated."),
        check("archive_exists", Path::new(path).exists(), "Archive existence was evaluated."),
        check("format_supported", !matches!(format, ArchiveFormat::Unknown), format!("Detected format: {:?}", format)),
        check("backend_available", backend_available(&format, false), "Read backend availability was evaluated."),
    ]
}

pub fn intent_checks_for_extract(path: &str, out: &str) -> Vec<IntentCheck> {
    let mut checks = intent_checks_for_archive_path(path);
    checks.push(check("output_path_present", !out.trim().is_empty(), "Extraction output path was evaluated."));
    checks
}

pub fn intent_checks_for_create(output: &str, inputs: &[String], format: &ArchiveFormat) -> Vec<IntentCheck> {
    vec![
        check("output_path_present", !output.trim().is_empty(), "Create output path was evaluated."),
        check("input_present", !inputs.is_empty(), "Input count was evaluated."),
        check("inputs_exist", inputs.iter().all(|p| Path::new(p).exists()), "Input existence was evaluated."),
        check("write_format_supported", !matches!(format, ArchiveFormat::Rar | ArchiveFormat::Unknown), format!("Requested create format: {:?}", format)),
        check("backend_available", backend_available(format, true), "Write backend availability was evaluated."),
    ]
}

fn choose_reader(format: &ArchiveFormat) -> Result<&'static str, ArcRarError> {
    match format {
        ArchiveFormat::Zip => detect_first(&[BackendTool{label:"unzip",cmd:"unzip"}]).or_else(|| detect_first(SEVENZ_TOOLS)).or_else(|| detect_first(TAR_TOOLS)).ok_or_else(|| ArcRarError::BackendUnavailable("zip reader not found (need unzip, 7z/7zz, or bsdtar/tar)".into())),
        ArchiveFormat::Tar | ArchiveFormat::TarGz => detect_first(TAR_TOOLS).ok_or_else(|| ArcRarError::BackendUnavailable("tar reader not found".into())),
        ArchiveFormat::SevenZ => detect_first(SEVENZ_TOOLS).ok_or_else(|| ArcRarError::BackendUnavailable("7z/7zz not found".into())),
        ArchiveFormat::Rar => detect_first(&[BackendTool{label:"unrar",cmd:"unrar"}]).or_else(|| detect_first(SEVENZ_TOOLS)).or_else(|| command_exists("bsdtar").then_some("bsdtar")).ok_or_else(|| ArcRarError::BackendUnavailable("RAR reader not found (need unrar, 7z/7zz, or bsdtar)".into())),
        ArchiveFormat::Unknown => Err(ArcRarError::UnsupportedFormat("unknown format".into())),
    }
}

fn choose_writer(format: &ArchiveFormat) -> Result<&'static str, ArcRarError> {
    match format {
        ArchiveFormat::Zip => if command_exists("zip") { Ok("zip") } else { detect_first(SEVENZ_TOOLS).ok_or_else(|| ArcRarError::BackendUnavailable("zip writer not found (need zip or 7z/7zz)".into())) },
        ArchiveFormat::Tar | ArchiveFormat::TarGz => detect_first(TAR_TOOLS).ok_or_else(|| ArcRarError::BackendUnavailable("tar writer not found".into())),
        ArchiveFormat::SevenZ => detect_first(SEVENZ_TOOLS).ok_or_else(|| ArcRarError::BackendUnavailable("7z/7zz writer not found".into())),
        ArchiveFormat::Rar => Err(ArcRarError::UnsupportedFormat("RAR write is intentionally unsupported".into())),
        ArchiveFormat::Unknown => Err(ArcRarError::UnsupportedFormat("unknown format".into())),
    }
}

fn parse_simple_lines(stdout: &str) -> Vec<ArchiveEntry> {
    stdout.lines().filter_map(|line| {
        let trimmed = line.trim();
        if trimmed.is_empty() { return None; }
        Some(ArchiveEntry { path: trimmed.to_string(), size: None, packed_size: None, modified: None, is_dir: trimmed.ends_with('/'), encrypted: false, method: None })
    }).collect()
}

pub fn list_archive(path: &str) -> Result<Vec<ArchiveEntry>, ArcRarError> {
    let format = sniff_format(path);
    if matches!(format, ArchiveFormat::Unknown) { return Err(ArcRarError::UnsupportedFormat(path.to_string())); }
    if !Path::new(path).exists() { return Err(ArcRarError::Io(format!("archive does not exist: {}", path))); }
    let reader = choose_reader(&format)?;
    let output = match (format.clone(), reader) {
        (ArchiveFormat::Zip, "unzip") => run_command("unzip", &["-Z1", path])?,
        (ArchiveFormat::SevenZ, tool) if tool == "7z" || tool == "7zz" => run_command(tool, &["l", "-ba", path])?,
        (ArchiveFormat::Rar, "unrar") => run_command("unrar", &["lb", path])?,
        (_, "bsdtar") => run_command("bsdtar", &["-tf", path])?,
        (_, "tar") => run_command("tar", &["-tf", path])?,
        (_, tool) if tool == "7z" || tool == "7zz" => run_command(tool, &["l", "-ba", path])?,
        _ => return Err(ArcRarError::BackendUnavailable("no list command path resolved".into())),
    };
    if !output.status.success() {
        return Err(ArcRarError::BackendUnavailable(String::from_utf8_lossy(&output.stderr).trim().to_string()));
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut entries = parse_simple_lines(&stdout);
    if matches!(format, ArchiveFormat::SevenZ) {
        entries = stdout.lines().filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with("--") || trimmed.starts_with("Path =") || trimmed.starts_with("Type =") || trimmed.starts_with("Physical Size =") { return None; }
            if trimmed.len() > 20 && trimmed.chars().nth(4) == Some('-') {
                let parts: Vec<&str> = trimmed.split_whitespace().collect();
                if parts.len() >= 6 {
                    let size = parts.get(3).and_then(|s| s.parse::<u64>().ok());
                    let name = parts[5..].join(" ");
                    return Some(ArchiveEntry { path: name, size, packed_size: None, modified: Some(format!("{} {}", parts[0], parts[1])), is_dir: parts.get(2) == Some(&"D"), encrypted: false, method: None });
                }
            }
            None
        }).collect();
    }
    Ok(entries)
}

pub fn info_archive(path: &str) -> Result<ArchiveInfo, ArcRarError> {
    let format = sniff_format(path);
    if matches!(format, ArchiveFormat::Unknown) { return Err(ArcRarError::UnsupportedFormat(path.to_string())); }
    let entries = list_archive(path)?;
    let backend_used = choose_reader(&format)?.to_string();
    Ok(ArchiveInfo {
        path: path.to_string(),
        format,
        entries: entries.len(),
        encrypted: false,
        backend_used,
        detected_by: if Path::new(path).exists() { "signature-or-extension".into() } else { "extension".into() },
    })
}

fn ensure_parent(path: &Path) -> Result<(), ArcRarError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| ArcRarError::Io(e.to_string()))?;
    }
    Ok(())
}

fn archive_entry_path_is_safe(path: &str) -> bool {
    let candidate = Path::new(path);
    if candidate.is_absolute() {
        return false;
    }
    !candidate.components().any(|component| matches!(component, std::path::Component::ParentDir | std::path::Component::RootDir | std::path::Component::Prefix(_)))
}

pub fn list_unsafe_archive_entries(path: &str) -> Result<Vec<String>, ArcRarError> {
    let entries = list_archive(path)?;
    Ok(entries
        .into_iter()
        .filter(|entry| !archive_entry_path_is_safe(&entry.path))
        .map(|entry| entry.path)
        .collect())
}

pub fn extract_archive(path: &str, out: &str) -> Result<OperationSummary, ArcRarError> {
    let format = sniff_format(path);
    if matches!(format, ArchiveFormat::Unknown) { return Err(ArcRarError::UnsupportedFormat(path.to_string())); }
    let unsafe_entries = list_unsafe_archive_entries(path)?;
    if !unsafe_entries.is_empty() {
        return Err(ArcRarError::Security(format!("archive contains unsafe extract paths: {}", unsafe_entries.join(", "))));
    }
    let out_path = PathBuf::from(out);
    fs::create_dir_all(&out_path).map_err(|e| ArcRarError::Io(e.to_string()))?;
    let reader = choose_reader(&format)?;
    let output = match (format.clone(), reader) {
        (ArchiveFormat::Zip, "unzip") => run_command("unzip", &["-o", path, "-d", out])?,
        (ArchiveFormat::SevenZ, tool) if tool == "7z" || tool == "7zz" => {
            let arg = format!("-o{}", out);
            run_command(tool, &["x", "-y", path, &arg])?
        }
        (ArchiveFormat::Rar, "unrar") => run_command("unrar", &["x", "-o+", path, out])?,
        (_, "bsdtar") => run_command("bsdtar", &["-xf", path, "-C", out])?,
        (_, "tar") => run_command("tar", &["-xf", path, "-C", out])?,
        (_, tool) if tool == "7z" || tool == "7zz" => {
            let arg = format!("-o{}", out);
            run_command(tool, &["x", "-y", path, &arg])?
        }
        _ => return Err(ArcRarError::BackendUnavailable("no extract command path resolved".into())),
    };
    if !output.status.success() {
        return Err(ArcRarError::BackendUnavailable(String::from_utf8_lossy(&output.stderr).trim().to_string()));
    }
    Ok(OperationSummary { ok: true, message: format!("extracted {} -> {}", path, out), output_path: Some(out.to_string()), accounted_for: true, intent_contract_satisfied: true, backend_used: Some(reader.to_string()) })
}

pub fn create_archive(output: &str, inputs: &[String], format: ArchiveFormat) -> Result<OperationSummary, ArcRarError> {
    if inputs.is_empty() { return Err(ArcRarError::InvalidInput("no inputs supplied".into())); }
    if inputs.iter().any(|p| !Path::new(p).exists()) { return Err(ArcRarError::InvalidInput("one or more input paths do not exist".into())); }
    let writer = choose_writer(&format)?;
    let out_path = PathBuf::from(output);
    ensure_parent(&out_path)?;
    let status = match (format.clone(), writer) {
        (ArchiveFormat::Zip, "zip") => {
            let mut cmd = Command::new("zip");
            cmd.arg("-r").arg(output);
            for i in inputs { cmd.arg(i); }
            cmd.status().map_err(|e| ArcRarError::BackendUnavailable(e.to_string()))?
        }
        (ArchiveFormat::Zip, tool) if tool == "7z" || tool == "7zz" => {
            let mut cmd = Command::new(tool);
            cmd.arg("a").arg(output);
            for i in inputs { cmd.arg(i); }
            cmd.status().map_err(|e| ArcRarError::BackendUnavailable(e.to_string()))?
        }
        (ArchiveFormat::SevenZ, tool) if tool == "7z" || tool == "7zz" => {
            let mut cmd = Command::new(tool);
            cmd.arg("a").arg(output);
            for i in inputs { cmd.arg(i); }
            cmd.status().map_err(|e| ArcRarError::BackendUnavailable(e.to_string()))?
        }
        (ArchiveFormat::Tar, tool) if tool == "tar" || tool == "bsdtar" => {
            let mut cmd = Command::new(tool);
            cmd.arg("-cf").arg(output);
            for i in inputs { cmd.arg(i); }
            cmd.status().map_err(|e| ArcRarError::BackendUnavailable(e.to_string()))?
        }
        (ArchiveFormat::TarGz, tool) if tool == "tar" || tool == "bsdtar" => {
            let mut cmd = Command::new(tool);
            cmd.arg("-czf").arg(output);
            for i in inputs { cmd.arg(i); }
            cmd.status().map_err(|e| ArcRarError::BackendUnavailable(e.to_string()))?
        }
        _ => return Err(ArcRarError::UnsupportedFormat("unsupported writer path".into())),
    };
    if !status.success() {
        return Err(ArcRarError::BackendUnavailable(format!("backend exited with status {}", status)));
    }
    Ok(OperationSummary { ok: true, message: format!("created {} from {} input(s)", output, inputs.len()), output_path: Some(output.to_string()), accounted_for: true, intent_contract_satisfied: true, backend_used: Some(writer.to_string()) })
}

pub fn test_archive(path: &str) -> Result<OperationSummary, ArcRarError> {
    let format = sniff_format(path);
    if matches!(format, ArchiveFormat::Unknown) { return Err(ArcRarError::UnsupportedFormat(path.to_string())); }
    let reader = choose_reader(&format)?;
    let output = match (format.clone(), reader) {
        (ArchiveFormat::Zip, "unzip") => run_command("unzip", &["-t", path])?,
        (ArchiveFormat::SevenZ, tool) if tool == "7z" || tool == "7zz" => run_command(tool, &["t", path])?,
        (ArchiveFormat::Rar, "unrar") => run_command("unrar", &["t", path])?,
        (_, "bsdtar") => run_command("bsdtar", &["-tf", path])?,
        (_, "tar") => run_command("tar", &["-tf", path])?,
        (_, tool) if tool == "7z" || tool == "7zz" => run_command(tool, &["t", path])?,
        _ => return Err(ArcRarError::BackendUnavailable("no test command path resolved".into())),
    };
    if !output.status.success() {
        return Err(ArcRarError::BackendUnavailable(String::from_utf8_lossy(&output.stderr).trim().to_string()));
    }
    Ok(OperationSummary { ok: true, message: format!("archive test passed for {}", path), output_path: None, accounted_for: true, intent_contract_satisfied: true, backend_used: Some(reader.to_string()) })
}

pub fn backend_doctor() -> BackendDoctor {
    let checks = ["zip", "unzip", "7z", "7zz", "tar", "bsdtar", "unrar"];
    let mut detected = vec![];
    let mut missing = vec![];
    for cmd in checks {
        if command_exists(cmd) { detected.push(cmd.to_string()); } else { missing.push(cmd.to_string()); }
    }
    BackendDoctor {
        detected_tools: detected,
        missing_tools: missing,
        advice: vec![
            "Install 7-Zip / p7zip / 7zz for 7z support.".into(),
            "Install unrar or ensure bsdtar/libarchive can read RAR on the host.".into(),
            "Use native shell integration per OS for best UX.".into(),
            "Autowrap + intent validation is now wired through all command planes; unmet required intents can block in strict mode.".into(),
        ],
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sniff_extension_fallbacks() {
        assert_eq!(sniff_format("demo.zip"), ArchiveFormat::Zip);
        assert_eq!(sniff_format("demo.tar.gz"), ArchiveFormat::TarGz);
        assert_eq!(sniff_format("demo.7z"), ArchiveFormat::SevenZ);
        assert_eq!(sniff_format("demo.rar"), ArchiveFormat::Rar);
    }

    #[test]
    fn unsafe_entry_detection_rejects_parent_segments() {
        assert!(!archive_entry_path_is_safe("../evil.txt"));
        assert!(!archive_entry_path_is_safe("/abs/path.txt"));
        assert!(archive_entry_path_is_safe("safe/file.txt"));
    }
}
