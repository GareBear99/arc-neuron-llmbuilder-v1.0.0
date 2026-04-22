use anyhow::{Context, Result};
use chrono::Utc;
use obi_receipts::ReceiptIndexEntry;
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

pub fn cache_root() -> PathBuf {
    if let Ok(custom) = std::env::var("OBI_CACHE_DIR") {
        return PathBuf::from(custom);
    }

    if cfg!(target_os = "windows") {
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            return Path::new(&local).join("omnibinary");
        }
    }

    if let Ok(home) = std::env::var("HOME") {
        return Path::new(&home).join(".cache").join("omnibinary");
    }

    PathBuf::from(".omnibinary-cache")
}

pub fn ensure_layout() -> Result<PathBuf> {
    let root = cache_root();
    for dir in ["inspects", "runs", "plans", "lowers", "decodes", "dispatch", "doctor", "env", "index", "core-gap", "fixtures", "reports"] {
        fs::create_dir_all(root.join(dir))
            .with_context(|| format!("failed to create cache directory {}", dir))?;
    }
    Ok(root)
}

fn sanitize_stem(stem: &str) -> String {
    stem.chars()
        .map(|c| match c {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' => c,
            _ => '-',
        })
        .collect()
}

pub fn write_json<T: Serialize>(category: &str, stem: &str, value: &T, sha256: Option<&str>) -> Result<PathBuf> {
    let root = ensure_layout()?;
    let safe_stem = sanitize_stem(stem);
    let category_dir = root.join(category);
    fs::create_dir_all(&category_dir).with_context(|| format!("failed to create {}", category_dir.display()))?;
    let path = category_dir.join(format!("{safe_stem}.json"));
    let bytes = serde_json::to_vec_pretty(value)?;
    fs::write(&path, bytes).with_context(|| format!("failed to write {}", path.display()))?;
    append_index(category, &safe_stem, &path, sha256)?;
    Ok(path)
}

fn append_index(category: &str, stem: &str, path: &Path, sha256: Option<&str>) -> Result<()> {
    let root = ensure_layout()?;
    let index_path = root.join("index").join("receipts.jsonl");
    let entry = ReceiptIndexEntry {
        created_at_utc: Utc::now(),
        category: category.to_string(),
        stem: stem.to_string(),
        path: path.display().to_string(),
        sha256: sha256.map(ToOwned::to_owned),
    };
    let line = serde_json::to_string(&entry)? + "\n";
    use std::io::Write;
    let mut file = fs::OpenOptions::new().create(true).append(true).open(&index_path)
        .with_context(|| format!("failed to open {}", index_path.display()))?;
    file.write_all(line.as_bytes())
        .with_context(|| format!("failed to append {}", index_path.display()))?;
    Ok(())
}

pub fn read_index(limit: usize) -> Result<Vec<ReceiptIndexEntry>> {
    let root = ensure_layout()?;
    let index_path = root.join("index").join("receipts.jsonl");
    if !index_path.exists() {
        return Ok(Vec::new());
    }
    let data = fs::read_to_string(&index_path)
        .with_context(|| format!("failed to read {}", index_path.display()))?;
    let mut entries = Vec::new();
    for line in data.lines().rev().take(limit) {
        let parsed: ReceiptIndexEntry = serde_json::from_str(line)
            .with_context(|| "failed to parse receipt index line")?;
        entries.push(parsed);
    }
    Ok(entries)
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CacheCategoryStat {
    pub category: String,
    pub file_count: usize,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CacheStats {
    pub root: String,
    pub categories: Vec<CacheCategoryStat>,
    pub total_receipts_indexed: usize,
}

pub fn stats() -> Result<CacheStats> {
    let root = ensure_layout()?;
    let mut categories = Vec::new();
    for category in ["inspects", "runs", "plans", "lowers", "decodes", "dispatch", "doctor", "env", "core-gap", "fixtures", "reports", "index"] {
        let dir = root.join(category);
        let count = if dir.exists() {
            fs::read_dir(&dir)
                .with_context(|| format!("failed to read {}", dir.display()))?
                .filter_map(|e| e.ok())
                .count()
        } else { 0 };
        categories.push(CacheCategoryStat { category: category.to_string(), file_count: count });
    }
    let total_receipts_indexed = read_index(usize::MAX)?.len();
    Ok(CacheStats { root: root.display().to_string(), categories, total_receipts_indexed })
}


pub fn summarize_index(limit_latest: usize) -> Result<obi_receipts::ReceiptSummary> {
    let entries = read_index(usize::MAX)?;
    let mut counts = std::collections::BTreeMap::<String, usize>::new();
    for entry in &entries {
        *counts.entry(entry.category.clone()).or_insert(0) += 1;
    }
    let latest_entries = entries.iter().take(limit_latest).cloned().collect();
    Ok(obi_receipts::ReceiptSummary {
        created_at_utc: Utc::now(),
        total_entries: entries.len(),
        categories: counts.into_iter().collect(),
        latest_entries,
    })
}

pub fn clear_generated_receipts() -> Result<Vec<String>> {
    let root = ensure_layout()?;
    let mut removed = Vec::new();
    for category in ["inspects", "runs", "plans", "lowers", "decodes", "dispatch", "doctor", "env", "core-gap", "fixtures", "reports"] {
        let dir = root.join(category);
        if !dir.exists() { continue; }
        for entry in fs::read_dir(&dir).with_context(|| format!("failed to read {}", dir.display()))? {
            let entry = entry?;
            let path = entry.path();
            if path.is_file() {
                fs::remove_file(&path).with_context(|| format!("failed to remove {}", path.display()))?;
                removed.push(path.display().to_string());
            }
        }
    }
    let index_path = root.join("index").join("receipts.jsonl");
    if index_path.exists() {
        fs::remove_file(&index_path).with_context(|| format!("failed to remove {}", index_path.display()))?;
        removed.push(index_path.display().to_string());
    }
    Ok(removed)
}


pub fn validate_index() -> Result<obi_receipts::CacheValidationReport> {
    let root = ensure_layout()?;
    let entries = read_index(usize::MAX)?;
    let mut issues = Vec::new();
    let mut missing_paths = 0usize;
    for entry in &entries {
        if !Path::new(&entry.path).exists() {
            missing_paths += 1;
            issues.push(obi_receipts::CacheValidationIssue {
                level: "error".to_string(),
                detail: format!("indexed path missing: {}", entry.path),
            });
        }
    }
    let mut orphan_receipts = 0usize;
    for category in ["inspects", "runs", "plans", "lowers", "decodes", "dispatch", "doctor", "env", "core-gap", "fixtures", "reports"] {
        let dir = root.join(category);
        if !dir.exists() { continue; }
        for entry in fs::read_dir(&dir).with_context(|| format!("failed to read {}", dir.display()))? {
            let path = entry?.path();
            if !path.is_file() { continue; }
            let p = path.display().to_string();
            if !entries.iter().any(|e| e.path == p) {
                orphan_receipts += 1;
                issues.push(obi_receipts::CacheValidationIssue {
                    level: "warn".to_string(),
                    detail: format!("receipt file missing from index: {}", p),
                });
            }
        }
    }
    Ok(obi_receipts::CacheValidationReport {
        created_at_utc: Utc::now(),
        cache_root: root.display().to_string(),
        index_entries_checked: entries.len(),
        missing_paths,
        orphan_receipts,
        ok: missing_paths == 0,
        issues,
    })
}
