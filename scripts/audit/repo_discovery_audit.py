#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "GareBear99/arc-neuron-llmbuilder-v1.0.0")
ROOT = Path.cwd()

STALE_PATTERNS = [
    r"feeds this corpus every day",
    r"nightly workflow",
    r"nightly ingest",
    r"daily 03:17",
    r"Daily \(and on-demand\)",
    r"ingest-operator-reviews\.yml \(daily\)",
]

JUNK_NAMES = {
    ".DS_Store",
    "__MACOSX",
    "FETCH_HEAD",
    "--json",
    "--method",
    "--repo",
    "--description",
    "--homepage",
}

REQUIRED_TOPICS = {
    "llm",
    "llmops",
    "benchmarking",
    "model-evaluation",
    "local-ai",
    "local-first-ai",
    "offline-ai",
    "ai-governance",
    "model-governance",
    "gguf",
}

def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)

def gh_json(args: list[str]) -> object:
    p = run(["gh", *args], check=False)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)

def add_result(results: list[dict], name: str, ok: bool, detail: str, critical: bool = False) -> None:
    results.append({"name": name, "ok": ok, "detail": detail, "critical": critical})

def main() -> int:
    results: list[dict] = []

    status = run(["git", "status", "--short"]).stdout.strip()
    add_result(results, "Local working tree clean", status == "", status or "clean", critical=True)

    prs = gh_json(["pr", "list", "--repo", REPO, "--state", "open", "--json", "number,title,url"])
    issues = gh_json(["issue", "list", "--repo", REPO, "--state", "open", "--limit", "50", "--json", "number,title,url"])
    add_result(results, "No open PRs", len(prs) == 0, f"{len(prs)} open PR(s)", critical=False)
    add_result(results, "No open issues", len(issues) == 0, f"{len(issues)} open issue(s)", critical=False)

    stale_hits: list[str] = []
    scan_paths = [ROOT / "README.md", ROOT / "docs", ROOT / ".github" / "workflows"]
    for base in scan_paths:
        if not base.exists():
            continue
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for path in files:
            if ".git" in path.parts:
                continue
            try:
                txt = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for pat in STALE_PATTERNS:
                if re.search(pat, txt, flags=re.I):
                    stale_hits.append(f"{path.relative_to(ROOT)} :: {pat}")
    add_result(results, "No stale ingest wording", not stale_hits, "\n".join(stale_hits) or "clean", critical=True)

    wf = ROOT / ".github/workflows/ingest-operator-reviews.yml"
    if wf.exists():
        wf_txt = wf.read_text(encoding="utf-8", errors="replace")
        has_dispatch = "workflow_dispatch:" in wf_txt
        has_schedule = re.search(r"^\s*schedule:", wf_txt, flags=re.M) is not None
        has_cron = re.search(r"^\s*-\s*cron:", wf_txt, flags=re.M) is not None
        checkout_v6 = "actions/checkout@v6" in wf_txt
        setup_v6 = "actions/setup-python@v6" in wf_txt
        add_result(
            results,
            "Workflow is manual-dispatch",
            has_dispatch and not has_schedule and not has_cron,
            f"workflow_dispatch={has_dispatch}, schedule={has_schedule}, cron={has_cron}",
            critical=True,
        )
        add_result(
            results,
            "Workflow actions are current",
            checkout_v6 and setup_v6,
            f"checkout@v6={checkout_v6}, setup-python@v6={setup_v6}",
            critical=False,
        )
    else:
        add_result(results, "Workflow exists", False, "missing .github/workflows/ingest-operator-reviews.yml", critical=True)

    try:
        protection = gh_json(["api", f"repos/{REPO}/branches/main/protection"])
        reviews = protection.get("required_pull_request_reviews") or {}
        approving = reviews.get("required_approving_review_count")
        codeowners = reviews.get("require_code_owner_reviews")
        admins = (protection.get("enforce_admins") or {}).get("enabled")
        add_result(
            results,
            "Branch protection restored",
            approving == 1 and codeowners is True and admins is True,
            f"approvals={approving}, codeowners={codeowners}, admins={admins}",
            critical=True,
        )
    except Exception as e:
        add_result(results, "Branch protection readable", False, str(e), critical=True)

    try:
        meta = gh_json([
            "repo", "view", REPO,
            "--json", "description,homepageUrl,repositoryTopics,latestRelease,usesCustomOpenGraphImage,isPrivate,isArchived,isFork,licenseInfo,primaryLanguage"
        ])
        topics = {t["name"] for t in meta.get("repositoryTopics", [])}
        missing_topics = sorted(REQUIRED_TOPICS - topics)
        add_result(
            results,
            "Repo is public active source",
            (not meta.get("isPrivate")) and (not meta.get("isArchived")) and (not meta.get("isFork")),
            f"private={meta.get('isPrivate')}, archived={meta.get('isArchived')}, fork={meta.get('isFork')}",
            critical=True,
        )
        add_result(
            results,
            "Description/homepage present",
            bool(meta.get("description")) and bool(meta.get("homepageUrl")),
            f"description={bool(meta.get('description'))}, homepage={meta.get('homepageUrl')}",
            critical=True,
        )
        add_result(results, "Release present", bool(meta.get("latestRelease")), (meta.get("latestRelease") or {}).get("tagName", "missing"), critical=True)
        add_result(results, "Custom social preview active", meta.get("usesCustomOpenGraphImage") is True, str(meta.get("usesCustomOpenGraphImage")), critical=False)
        add_result(results, "Discovery topics present", not missing_topics, "missing: " + ", ".join(missing_topics) if missing_topics else "all required topics present", critical=False)
        add_result(
            results,
            "MIT/Python detected",
            (meta.get("licenseInfo") or {}).get("key") == "mit" and (meta.get("primaryLanguage") or {}).get("name") == "Python",
            f"license={(meta.get('licenseInfo') or {}).get('key')}, lang={(meta.get('primaryLanguage') or {}).get('name')}",
            critical=False,
        )
    except Exception as e:
        add_result(results, "Repo metadata readable", False, str(e), critical=True)

    asset = ROOT / "assets/brand/social-preview.svg"
    add_result(results, "Social preview SVG committed", asset.exists(), str(asset), critical=False)

    junk = []
    for p in ROOT.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.name in JUNK_NAMES:
            junk.append(str(p.relative_to(ROOT)))
    add_result(results, "No junk files", not junk, "\n".join(junk) or "clean", critical=True)

    large = []
    for p in ROOT.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        try:
            if p.stat().st_size > 5 * 1024 * 1024:
                large.append(f"{p.relative_to(ROOT)} ({p.stat().st_size} bytes)")
        except OSError:
            pass
    add_result(results, "No unexpected large files", not large, "\n".join(large) or "clean", critical=False)

    failed = [r for r in results if not r["ok"]]
    critical_failed = [r for r in failed if r["critical"]]

    lines = [
        "# ARC-Neuron v1.0.0 Repo Discovery Audit",
        "",
        f"Repository: `{REPO}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for r in results:
        status_text = "✅ PASS" if r["ok"] else ("❌ FAIL" if r["critical"] else "⚠️ WARN")
        detail = str(r["detail"]).replace("\n", "<br>")
        lines.append(f"| {r['name']} | {status_text} | {detail} |")
    lines.extend([
        "",
        f"Critical failures: **{len(critical_failed)}**",
        f"Warnings/non-critical failures: **{len(failed) - len(critical_failed)}**",
    ])
    report = "\n".join(lines)
    print(report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text(report + "\n", encoding="utf-8")

    return 1 if critical_failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
