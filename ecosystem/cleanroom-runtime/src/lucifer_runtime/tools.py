from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from arc_kernel.schemas import Capability, Proposal, RiskLevel
from verifier.safety import path_within_workspace


@dataclass
class ToolResult:
    success: bool
    outputs: Dict[str, Any]


class FileSystemAdapter:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace_root / path).resolve()
        if not path_within_workspace(self.workspace_root, candidate):
            raise ValueError(f"Path escapes workspace root: {path}")
        return candidate

    def read_file(self, path: str) -> ToolResult:
        try:
            target = self._resolve(path)
        except ValueError as exc:
            return ToolResult(False, {"error": str(exc)})
        if not target.exists() or not target.is_file():
            return ToolResult(False, {"error": f"File not found: {path}"})
        return ToolResult(True, {"path": str(target.relative_to(self.workspace_root)), "content": target.read_text(encoding="utf-8")})

    def write_file(self, path: str, content: str, dry_run: bool = False) -> ToolResult:
        try:
            target = self._resolve(path)
        except ValueError as exc:
            return ToolResult(False, {"error": str(exc)})
        previous_exists = target.exists()
        previous_content = target.read_text(encoding="utf-8") if previous_exists and target.is_file() else None
        if dry_run:
            return ToolResult(
                True,
                {
                    "path": str(target.relative_to(self.workspace_root)),
                    "dry_run": True,
                    "bytes": len(content.encode("utf-8")),
                    "undo": {"action": "restore_file", "path": path, "existed": previous_exists, "content": previous_content},
                },
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(
            True,
            {
                "path": str(target.relative_to(self.workspace_root)),
                "written": True,
                "bytes": len(content.encode("utf-8")),
                "undo": {"action": "restore_file", "path": path, "existed": previous_exists, "content": previous_content},
            },
        )

    def delete_file(self, path: str, dry_run: bool = False) -> ToolResult:
        try:
            target = self._resolve(path)
        except ValueError as exc:
            return ToolResult(False, {"error": str(exc)})
        if not target.exists() or not target.is_file():
            return ToolResult(False, {"error": f"File not found: {path}"})
        previous_content = target.read_text(encoding="utf-8")
        if dry_run:
            return ToolResult(
                True,
                {
                    "path": str(target.relative_to(self.workspace_root)),
                    "dry_run": True,
                    "would_delete": True,
                    "undo": {"action": "restore_file", "path": path, "existed": True, "content": previous_content},
                },
            )
        target.unlink()
        return ToolResult(
            True,
            {
                "path": str(target.relative_to(self.workspace_root)),
                "deleted": True,
                "undo": {"action": "restore_file", "path": path, "existed": True, "content": previous_content},
            },
        )

    def restore_file(self, path: str, existed: bool, content: str | None) -> ToolResult:
        try:
            target = self._resolve(path)
        except ValueError as exc:
            return ToolResult(False, {"error": str(exc)})
        if not existed:
            if target.exists():
                target.unlink()
            return ToolResult(True, {"path": path, "restored": True, "mode": "deleted_new_file"})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content or "", encoding="utf-8")
        return ToolResult(True, {"path": path, "restored": True, "mode": "restored_previous_content"})


class ShellAdapter:
    ALLOWLIST = {"pwd", "ls", "echo"}

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = str(Path(workspace_root).resolve())

    def run(self, command: str, dry_run: bool = False) -> ToolResult:
        parts = shlex.split(command)
        if not parts:
            return ToolResult(False, {"error": "Empty shell command."})
        if parts[0] not in self.ALLOWLIST:
            return ToolResult(False, {"error": f"Command not allowlisted: {parts[0]}"})
        if dry_run:
            return ToolResult(True, {"dry_run": True, "command": command})
        completed = subprocess.run(parts, cwd=self.workspace_root, capture_output=True, text=True, timeout=5)
        return ToolResult(
            completed.returncode == 0,
            {
                "command": command,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "returncode": completed.returncode,
            },
        )


class ToolRegistry:
    def __init__(self, workspace_root: str | Path = ".") -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.fs = FileSystemAdapter(self.workspace_root)
        self.shell = ShellAdapter(self.workspace_root)

    def capability_for_intent(self, intent_type: str) -> Capability:
        mapping = {
            "analysis": Capability("analysis", "Non-mutating analysis", RiskLevel.LOW),
            "read_file": Capability("filesystem.read", "Read-only filesystem access", RiskLevel.LOW),
            "write_file": Capability(
                "filesystem.write",
                "Filesystem write access",
                RiskLevel.MEDIUM,
                ["mutates files"],
                ["path_guard", "workspace_guard"],
            ),
            "delete_file": Capability(
                "filesystem.delete",
                "Destructive filesystem action",
                RiskLevel.HIGH,
                ["deletes files"],
                ["path_guard", "workspace_guard"],
                requires_confirmation=True,
            ),
            "shell_command": Capability(
                "shell.exec",
                "Allowlisted shell access",
                RiskLevel.MEDIUM,
                ["runs allowlisted shell command"],
                ["allowlist_guard"],
            ),
            "unknown": Capability("unknown", "Unknown or unsupported intent", RiskLevel.CRITICAL),
        }
        return mapping[intent_type]

    def proposal_for_intent(self, intent_type: str, text: str, proposed_by: str) -> Proposal:
        capability = self.capability_for_intent(intent_type)
        params = self._params_from_text(intent_type, text)
        return Proposal(
            action=intent_type,
            capability=capability,
            params=params,
            proposed_by=proposed_by,
            rationale=f"Routed from intent type: {intent_type}",
        )

    def _params_from_text(self, intent_type: str, text: str) -> Dict[str, Any]:
        stripped = text.strip()
        lowered = stripped.lower()
        if intent_type == "read_file":
            path = stripped.split()[-1]
            return {"path": path}
        if intent_type == "delete_file":
            path = stripped.split()[-1]
            return {"path": path}
        if intent_type == "write_file":
            if "::" in stripped:
                left, content = stripped.split("::", 1)
                path = left.split()[-1]
                return {"path": path, "content": content.strip()}
            path = stripped.split()[-1]
            return {"path": path, "content": ""}
        if intent_type == "shell_command":
            command = stripped
            for prefix in ["run command", "shell"]:
                if lowered.startswith(prefix):
                    command = stripped[len(prefix):].strip()
                    break
            return {"command": command}
        return {"text": stripped}

    def execute(self, proposal: Proposal) -> ToolResult:
        params = proposal.params
        dry_run = bool(params.get("dry_run", False))
        if proposal.action == "analysis":
            return ToolResult(True, {"echo": params, "action": proposal.action})
        if proposal.action == "read_file":
            return self.fs.read_file(params["path"])
        if proposal.action == "write_file":
            return self.fs.write_file(params["path"], params.get("content", ""), dry_run=dry_run)
        if proposal.action == "delete_file":
            return self.fs.delete_file(params["path"], dry_run=dry_run)
        if proposal.action == "shell_command":
            return self.shell.run(params["command"], dry_run=dry_run)
        return ToolResult(False, {"error": f"Unsupported action: {proposal.action}"})

    def rollback(self, undo: Dict[str, Any]) -> ToolResult:
        if undo.get("action") == "restore_file":
            return self.fs.restore_file(undo["path"], existed=bool(undo.get("existed")), content=undo.get("content"))
        return ToolResult(False, {"error": "Unsupported rollback action."})
