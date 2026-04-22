use anyhow::Result;
use std::path::Path;

pub fn execute(path: &Path, args: &[String]) -> Result<i32> {
    let status = obi_loader::run_native(path, args)?;
    Ok(status.code().unwrap_or_default())
}
