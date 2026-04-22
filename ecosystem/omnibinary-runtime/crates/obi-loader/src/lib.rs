use anyhow::{Context, Result};
use std::path::Path;
use std::process::{Command, ExitStatus};

pub fn run_native(path: &Path, args: &[String]) -> Result<ExitStatus> {
    let status = Command::new(path)
        .args(args)
        .status()
        .with_context(|| format!("failed to execute {}", path.display()))?;
    Ok(status)
}
