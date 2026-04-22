from __future__ import annotations


class LocalEchoModel:
    def __init__(self, name: str = "local-echo") -> None:
        self.name = name

    def generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> str:
        return f"[{self.name}] {prompt}"
