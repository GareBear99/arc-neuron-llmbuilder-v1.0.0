from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".md", ".txt", ".toml",
    ".sh", ".bash", ".zsh", ".html", ".css", ".sql", ".java", ".go", ".rs", ".cpp", ".c",
}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".mypy_cache"}


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and (path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"README", "LICENSE"}):
            yield path


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""


def summarize_purpose(root: Path) -> str:
    for name in ["README.md", "README.txt", "README"]:
        candidate = root / name
        if candidate.exists():
            text = read_text_safe(candidate).strip().splitlines()
            for line in text:
                line = line.strip(" #	")
                if line:
                    return line[:280]
    return f"Repository capsule for {root.name}."


def build_module_map(root: Path, files: list[Path]) -> list[dict]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for path in files:
        rel = path.relative_to(root).as_posix()
        top = rel.split("/")[0]
        buckets[top].append(rel)
    items = []
    for module, rels in sorted(buckets.items()):
        summary = f"Top-level module or file group '{module}' containing {len(rels)} tracked files."
        items.append({"module": module, "summary": summary, "files": rels[:20]})
    return items[:50]


def build_symbol_index(root: Path, files: list[Path]) -> list[dict]:
    symbols = []
    for path in files:
        text = read_text_safe(path)
        rel = path.relative_to(root).as_posix()
        for line in text.splitlines()[:400]:
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                name = stripped.split()[1].split("(")[0].split(":")[0]
                kind = "function" if stripped.startswith("def ") else "class"
                symbols.append({"symbol": name, "kind": kind, "file": rel, "references": []})
            elif stripped.startswith("function "):
                name = stripped.split()[1].split("(")[0]
                symbols.append({"symbol": name, "kind": "function", "file": rel, "references": []})
    return symbols[:200]


def build_dependency_graph(root: Path, files: list[Path]) -> list[dict]:
    edges = []
    for path in files:
        text = read_text_safe(path)
        rel = path.relative_to(root).as_posix()
        for line in text.splitlines()[:300]:
            s = line.strip()
            if s.startswith("import "):
                target = s.replace("import ", "", 1).split(" as ")[0].strip()
                edges.append({"source": rel, "target": target, "relation": "imports"})
            elif s.startswith("from ") and " import " in s:
                target = s.split(" import ")[0].replace("from ", "", 1).strip()
                edges.append({"source": rel, "target": target, "relation": "imports_from"})
        if len(edges) > 300:
            break
    return edges[:300]


def build_test_map(root: Path, files: list[Path]) -> list[dict]:
    tests = []
    non_tests = [p.relative_to(root).as_posix() for p in files if "test" not in p.name.lower()][:40]
    for path in files:
        rel = path.relative_to(root).as_posix()
        if "test" in rel.lower():
            tests.append({"test": rel, "covers": non_tests[:5]})
    return tests[:100]


def build_hot_zones(root: Path, files: list[Path]) -> list[dict]:
    hot = []
    counts = Counter(p.suffix.lower() or "<noext>" for p in files)
    for path in files[:20]:
        rel = path.relative_to(root).as_posix()
        reason = "entry doc" if rel.lower().startswith("readme") else "tracked source surface"
        risk = "medium" if path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx"} else "low"
        hot.append({"surface": rel, "reason": reason, "risk_level": risk})
    if counts:
        hot.append({"surface": "repo-wide", "reason": f"Most common tracked file type is {counts.most_common(1)[0][0]}", "risk_level": "info"})
    return hot[:25]


def build_unknowns(root: Path, files: list[Path]) -> list[str]:
    unknowns = []
    if not any((root / name).exists() for name in ["README.md", "README.txt", "README"]):
        unknowns.append("No README found; purpose summary may be weak.")
    if not any("test" in p.name.lower() for p in files):
        unknowns.append("No obvious test files detected.")
    if not any(p.suffix.lower() in {".py", ".js", ".ts", ".go", ".rs", ".java"} for p in files):
        unknowns.append("No common source-code files detected in tracked set.")
    unknowns.append("Commit-history ingestion is not implemented in this local capsule builder.")
    return unknowns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--output", default="repo_state_capsule.sample.json")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    files = list(iter_files(root))
    capsule = {
        "repo_id": root.as_posix(),
        "name": root.name,
        "default_branch": "unknown",
        "purpose_summary": summarize_purpose(root),
        "entry_points": [p.relative_to(root).as_posix() for p in files[:10]],
        "module_map": build_module_map(root, files),
        "symbol_index": build_symbol_index(root, files),
        "dependency_graph": build_dependency_graph(root, files),
        "test_map": build_test_map(root, files),
        "hot_zones": build_hot_zones(root, files),
        "recent_changes": [],
        "unknowns": build_unknowns(root, files),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(capsule, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "repo": root.as_posix(), "tracked_files": len(files), "output": out.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
