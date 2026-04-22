from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class StreamEvent:
    text: str
    sequence: int
    chars_emitted: int
    words_emitted: int
    estimated_tokens: int
    prompt_chars: int = 0
    prompt_words: int = 0
    prompt_characters_used: int = 0
    prompt_word_tokens: int = 0
    templated_prompt_chars: int = 0
    completion_chars: int = 0
    completion_words: int = 0
    completion_characters_generated: int = 0
    completion_word_tokens: int = 0
    exact_prompt_tokens: int | None = None
    exact_completion_tokens: int | None = None
    exact_total_tokens: int | None = None
    elapsed_seconds: float = 0.0
    chars_per_second: float = 0.0
    words_per_second: float = 0.0
    done: bool = False


class BaseModel(Protocol):
    def generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> str: ...


class StreamingModel(BaseModel, Protocol):
    def stream_generate(self, prompt: str, context: dict | None = None, options: dict | None = None) -> Iterator[StreamEvent]: ...


class RouterModel(BaseModel, Protocol):
    pass


class PlannerModel(BaseModel, Protocol):
    pass


class CodeModel(BaseModel, Protocol):
    pass


class CriticModel(BaseModel, Protocol):
    pass


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, BaseModel] = {}

    def register(self, name: str, backend: BaseModel) -> None:
        self._backends[name] = backend

    def get(self, name: str) -> BaseModel:
        return self._backends[name]

    def names(self) -> list[str]:
        return sorted(self._backends.keys())
