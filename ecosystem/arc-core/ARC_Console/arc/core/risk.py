from __future__ import annotations
from math import log1p

def score_event(confidence: float, severity: int, watchlisted: bool, related_edges: int, event_count_7d: int) -> float:
    score = (confidence * 50.0) + (severity * 4.0) + min(18.0, log1p(event_count_7d) * 6.0) + min(12.0, related_edges * 1.5)
    if watchlisted:
        score += 18.0
    return round(min(100.0, score), 2)

def impact_band(score: float) -> str:
    if score >= 80: return "critical"
    if score >= 60: return "high"
    if score >= 35: return "medium"
    return "low"
