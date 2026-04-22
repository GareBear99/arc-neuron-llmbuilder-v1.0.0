"""EpisodicRetrieval — "what happened last time I tried this?"

The memory subsystem archives, ranks, and retires. The FixNet stores
repair patterns. But nothing answers the most useful question an agent
can ask before taking an action:

    "Have I attempted something like this before, and what happened?"

EpisodicRetrieval closes this gap with TF-IDF similarity search over
the kernel event log and FixNet repair archive — no embeddings, no
external models, no network. Pure in-process text matching.

Two retrieval modes:

  action_lookup(description)
    → "before I attempt this action, what happened last time?"
    → returns: prior receipts, outcomes, FixNet fixes triggered

  failure_lookup(error_signature)
    → "I just saw this error — has the system seen it before?"
    → returns: matching FixNet entries ranked by similarity

Results are injected into WorldModel for GoalEngine and Planner access,
and emitted as kernel evaluation events for audit.

Upgrade path: swap the TF-IDF scorer for an embedding model later
without changing the interface. The Protocol contract is stable.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── TF-IDF engine (zero-dep) ──────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text.lower())


def _tf(tokens: list[str]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = max(len(tokens), 1)
    return {t: c / total for t, c in counts.items()}


def _idf(term: str, corpus: list[list[str]]) -> float:
    n = len(corpus)
    df = sum(1 for doc in corpus if term in doc)
    return math.log((n + 1) / (df + 1)) + 1.0


def _tfidf_score(query: str, document: str, corpus_tokens: list[list[str]]) -> float:
    q_tokens = _tokenize(query)
    d_tokens = _tokenize(document)
    if not q_tokens or not d_tokens:
        return 0.0
    tf_d = _tf(d_tokens)
    score = 0.0
    for term in set(q_tokens):
        if term in tf_d:
            idf = _idf(term, corpus_tokens)
            score += tf_d[term] * idf
    return round(min(1.0, score / max(len(set(q_tokens)), 1)), 4)


# ── Retrieval result ──────────────────────────────────────────────────────────

@dataclass
class EpisodicMatch:
    source: str           # "kernel_receipt" | "fixnet" | "curriculum"
    match_id: str
    similarity: float
    summary: str
    outcome: str          # "success" | "failure" | "partial" | "unknown"
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodicResult:
    query: str
    mode: str             # "action_lookup" | "failure_lookup"
    matches: list[EpisodicMatch]
    top_outcome: str      # "success" | "failure" | "mixed" | "unknown"
    top_similarity: float
    recommendation: str   # "proceed" | "caution" | "avoid" | "no_history"
    timestamp: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "episodic_result"
        return d

    def has_relevant_history(self) -> bool:
        return bool(self.matches) and self.top_similarity >= 0.15


# ── EpisodicRetrieval ─────────────────────────────────────────────────────────

class EpisodicRetrieval:
    """Episodic memory retrieval over kernel log and FixNet archive.

    Args:
        runtime:        LuciferRuntime for kernel and FixNet access.
        top_k:          Max results to return (default 5).
        min_similarity: Discard matches below this threshold (default 0.08).
        inject_world_model: Write top result into WorldModel facts (default True).
    """

    def __init__(
        self,
        runtime: Any = None,
        *,
        top_k: int = 5,
        min_similarity: float = 0.08,
        inject_world_model: bool = True,
    ) -> None:
        self._runtime = runtime
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.inject_world_model = inject_world_model
        self._lookup_count = 0

    def wire(self, runtime: Any) -> None:
        self._runtime = runtime

    # ── Public API ────────────────────────────────────────────────────────────

    def action_lookup(self, description: str) -> EpisodicResult:
        """Retrieve prior episodes similar to a planned action.

        Call this BEFORE taking an action to surface relevant history.

        Args:
            description: Natural-language description of the planned action.

        Returns:
            EpisodicResult with ranked prior episodes.
        """
        self._lookup_count += 1
        candidates = self._collect_action_candidates()
        corpus_tokens = [_tokenize(c["text"]) for c in candidates]
        matches = self._rank(description, candidates, corpus_tokens)
        result = self._build_result(description, "action_lookup", matches)
        self._finalize(result)
        return result

    def failure_lookup(self, error_signature: str) -> EpisodicResult:
        """Retrieve FixNet entries matching an observed error signature.

        Call this on any execution failure to surface known solutions.

        Args:
            error_signature: Error string, exception message, or identifier.

        Returns:
            EpisodicResult with ranked FixNet matches.
        """
        self._lookup_count += 1
        candidates = self._collect_fixnet_candidates()
        corpus_tokens = [_tokenize(c["text"]) for c in candidates]
        matches = self._rank(error_signature, candidates, corpus_tokens)
        result = self._build_result(error_signature, "failure_lookup", matches)
        self._finalize(result)
        return result

    def status(self) -> dict[str, Any]:
        return {
            "lookup_count": self._lookup_count,
            "sources": ["kernel_receipts", "fixnet", "curriculum"],
        }

    # ── Data collection ───────────────────────────────────────────────────────

    def _collect_action_candidates(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        # From kernel event log — completed receipt events
        if self._runtime:
            kernel = getattr(self._runtime, "kernel", None)
            if kernel:
                try:
                    state = kernel.state()
                    for r in (state.receipts or [])[-100:]:
                        outputs = r.get("outputs", {})
                        text = " ".join([
                            str(r.get("proposal_id", "")),
                            str(outputs.get("path", "")),
                            str(outputs.get("content", ""))[:200],
                        ])
                        candidates.append({
                            "id": r.get("receipt_id", "?"),
                            "text": text,
                            "outcome": "success" if r.get("success") else "failure",
                            "timestamp": r.get("created_at", ""),
                            "source": "kernel_receipt",
                            "payload": r,
                        })
                except Exception:
                    pass

        # From curriculum memory
        if self._runtime:
            try:
                curriculum = getattr(self._runtime, "curriculum", None)
                if curriculum:
                    stats = curriculum.stats()
                    for theme in stats.get("top_themes", []):
                        text = f"theme {theme.get('name','')} outcome {theme.get('last_outcome','')}"
                        candidates.append({
                            "id": f"curriculum:{theme.get('name','')}",
                            "text": text,
                            "outcome": theme.get("last_outcome", "unknown"),
                            "timestamp": theme.get("last_seen_at", ""),
                            "source": "curriculum",
                            "payload": theme,
                        })
            except Exception:
                pass

        return candidates

    def _collect_fixnet_candidates(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if not self._runtime:
            return candidates
        fixnet = getattr(self._runtime, "fixnet", None)
        if not fixnet:
            return candidates
        try:
            stats = self._runtime.fixnet_stats()
            for case in stats.get("cases", [])[-200:]:
                text = " ".join([
                    str(case.get("error_type", "")),
                    str(case.get("error_signature", "")),
                    str(case.get("solution", "")),
                    str(case.get("summary", "")),
                ])
                candidates.append({
                    "id": case.get("fix_id", "?"),
                    "text": text,
                    "outcome": "success",  # FixNet entries are known solutions
                    "timestamp": case.get("created_at", ""),
                    "source": "fixnet",
                    "payload": case,
                })
        except Exception:
            pass
        return candidates

    # ── Ranking ───────────────────────────────────────────────────────────────

    def _rank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        corpus_tokens: list[list[str]],
    ) -> list[EpisodicMatch]:
        if not candidates:
            return []
        scored = []
        for i, c in enumerate(candidates):
            sim = _tfidf_score(query, c["text"], corpus_tokens)
            if sim >= self.min_similarity:
                scored.append((sim, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        matches = []
        for sim, c in scored[: self.top_k]:
            matches.append(EpisodicMatch(
                source=c["source"],
                match_id=c["id"],
                similarity=sim,
                summary=c["text"][:120],
                outcome=c.get("outcome", "unknown"),
                timestamp=c.get("timestamp", ""),
                payload=c.get("payload", {}),
            ))
        return matches

    def _build_result(
        self,
        query: str,
        mode: str,
        matches: list[EpisodicMatch],
    ) -> EpisodicResult:
        if not matches:
            return EpisodicResult(
                query=query, mode=mode, matches=[],
                top_outcome="unknown", top_similarity=0.0,
                recommendation="no_history",
            )

        top = matches[0]
        outcomes = [m.outcome for m in matches]
        success_count = outcomes.count("success")
        failure_count = outcomes.count("failure")

        if success_count > failure_count:
            top_outcome = "success"
        elif failure_count > success_count:
            top_outcome = "failure"
        elif success_count == failure_count and success_count > 0:
            top_outcome = "mixed"
        else:
            top_outcome = "unknown"

        if top.similarity < 0.10:
            recommendation = "no_history"
        elif top_outcome == "failure" and failure_count >= 2:
            recommendation = "avoid"
        elif top_outcome == "failure":
            recommendation = "caution"
        elif top_outcome == "mixed":
            recommendation = "caution"
        else:
            recommendation = "proceed"

        return EpisodicResult(
            query=query,
            mode=mode,
            matches=matches,
            top_outcome=top_outcome,
            top_similarity=top.similarity,
            recommendation=recommendation,
        )

    # ── Side effects ──────────────────────────────────────────────────────────

    def _finalize(self, result: EpisodicResult) -> None:
        # Inject into world model
        if self.inject_world_model and self._runtime:
            wm = getattr(self._runtime, "world_model", None)
            if wm:
                try:
                    wm.update_fact("episodic_last_query", result.query[:80])
                    wm.update_fact("episodic_last_recommendation", result.recommendation)
                    wm.update_fact("episodic_last_top_outcome", result.top_outcome)
                    wm.update_fact("episodic_last_similarity", result.top_similarity)
                    wm.update_fact("episodic_last_matches", [m.to_dict() for m in result.matches[:3]])
                except Exception:
                    pass

        # Kernel event
        if self._runtime:
            kernel = getattr(self._runtime, "kernel", None)
            if kernel:
                try:
                    kernel.record_evaluation("episodic_retrieval", result.to_dict())
                except Exception:
                    pass
