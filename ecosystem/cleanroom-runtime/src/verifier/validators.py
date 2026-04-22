from __future__ import annotations

from typing import Any, Dict, List

from arc_kernel.schemas import Proposal
from lucifer_runtime.tools import ToolResult


def validate_result(proposal: Proposal, result: ToolResult) -> List[Dict[str, Any]]:
    validators: List[Dict[str, Any]] = []
    validators.append({"validator": "execution_success", "passed": result.success})
    if proposal.action in {"read_file", "write_file", "delete_file"}:
        validators.append({"validator": "path_returned", "passed": "path" in result.outputs or "error" in result.outputs})
    if proposal.action == "shell_command":
        validators.append({"validator": "allowlisted_command_result", "passed": "returncode" in result.outputs or "error" in result.outputs})
    return validators
