from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RouteResult:
    intent_type: str
    confidence: float


class IntentRouter:
    def classify(self, text: str) -> RouteResult:
        lowered = text.lower().strip()
        if any(token in lowered for token in ["delete", "remove", "rm ", "wipe"]):
            return RouteResult("delete_file", 0.95)
        if any(token in lowered for token in ["write", "create file", "save", "append"]):
            return RouteResult("write_file", 0.85)
        if any(token in lowered for token in ["read", "show file", "cat "]):
            return RouteResult("read_file", 0.9)
        if any(token in lowered for token in ["ls", "pwd", "echo", "shell", "run command"]):
            return RouteResult("shell_command", 0.8)
        if any(token in lowered for token in ["list", "analyze", "inspect", "what is", "compare"]):
            return RouteResult("analysis", 0.7)
        return RouteResult("unknown", 0.25)
