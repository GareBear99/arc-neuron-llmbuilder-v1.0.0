from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from adapters.base import ModelAdapter, ModelResponse

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_']+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _norm(counter: Counter[str]) -> float:
    return math.sqrt(sum(v * v for v in counter.values())) or 1.0


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    denom = _norm(a) * _norm(b)
    numer = sum(v * b.get(k, 0) for k, v in a.items())
    return numer / denom if denom else 0.0


class ExemplarAdapter(ModelAdapter):
    name = "exemplar"
    promotable = True

    def __init__(self, artifact: str | None = None, top_k: int = 3, **_: Any) -> None:
        if not artifact:
            raise ValueError("artifact is required for exemplar adapter")
        self.artifact_path = Path(artifact)
        payload = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "records" not in payload:
            self.artifact_path, payload = self._resolve_manifest_payload(self.artifact_path, payload)
        self.model = payload.get("candidate_id", self.artifact_path.stem)
        self.top_k = int(top_k)
        self.records: list[dict[str, Any]] = payload.get("records", [])
        self._vectors: list[Counter[str]] = [Counter(r.get("prompt_tokens", [])) for r in self.records]

    def _resolve_manifest_payload(self, manifest_path: Path, payload: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        candidates: list[Path] = []
        output_file = payload.get("output_file")
        if output_file:
            candidates.append((manifest_path.parent / str(output_file)).resolve())
        paths_artifact = payload.get("paths", {}).get("artifact") if isinstance(payload.get("paths"), dict) else None
        if paths_artifact:
            path_value = Path(str(paths_artifact))
            candidates.append(path_value)
            candidates.append((manifest_path.parent / path_value.name).resolve())
        for candidate in candidates:
            if candidate.exists():
                return candidate, json.loads(candidate.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"could not resolve exemplar payload from manifest: {manifest_path}")

    def backend_identity(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "artifact": str(self.artifact_path),
            "candidate": self.model,
            "records": len(self.records),
            "top_k": self.top_k,
        }

    def healthcheck(self) -> dict[str, Any]:
        return {
            "ok": self.artifact_path.exists() and bool(self.records),
            "adapter": self.name,
            "artifact": str(self.artifact_path),
            "records": len(self.records),
        }

    def generate(self, prompt: str, *, system_prompt: str = "", context: dict | None = None) -> ModelResponse:
        started = time.perf_counter()
        tokens = Counter(_tokenize(prompt))
        scored: list[tuple[float, dict[str, Any]]] = []
        for vec, record in zip(self._vectors, self.records):
            score = _cosine(tokens, vec)
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        chosen = scored[: self.top_k] if scored else []

        lines: list[str] = []
        if system_prompt:
            lines.append(system_prompt.strip())
        if context and context.get("capability"):
            lines.append(f"Capability: {context['capability']}")

        if not chosen:
            lines.append(
                "No strong exemplar match was found. Preserve constraints, state unknowns, choose the smallest safe next step, and verify with evidence."
            )
        else:
            best = chosen[0][1]
            best_text = (best.get("target") or best.get("response") or "").strip()
            if best_text:
                lines.append(best_text)
            if len(chosen) > 1:
                lines.append("Supporting patterns:")
                for score, record in chosen[1:]:
                    summary = record.get("target") or record.get("response") or record.get("prompt") or ""
                    summary = " ".join(str(summary).split())[:200]
                    lines.append(f"- {summary}")
            lines.append("Confidence: bounded by retrieved exemplars and prompt overlap.")

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return ModelResponse(
            text="\n".join(line for line in lines if line),
            meta={
                "adapter": self.name,
                "artifact": str(self.artifact_path),
                "matches": [
                    {
                        "score": round(score, 4),
                        "source_repo": rec.get("source_repo"),
                        "capability": rec.get("capability"),
                        "source_file": rec.get("source_file"),
                    }
                    for score, rec in chosen
                ],
            },
            ok=True,
            latency_ms=latency_ms,
            backend_identity=f"{self.name}:{self.model}",
        )
