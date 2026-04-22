from __future__ import annotations

import difflib
from typing import Any

from .models import NoveltyDecision
from .ledger import FixLedger


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


class FixNoveltyFilter:
    """Decides whether a new fix is novel, duplicate, or variant.

    ARC-side equivalent of LuciferAI's SmartUploadFilter.
    """

    def __init__(self, ledger: FixLedger) -> None:
        self.ledger = ledger

    def decide(
        self,
        *,
        fix_id: str,
        error_signature: str,
        error_type: str,
        solution: str,
        min_duplicate: float = 0.92,
        min_variant: float = 0.75,
    ) -> NoveltyDecision:
        best_id = None
        best_score = 0.0
        best_kind = 'novel'
        for row in self.ledger.list_fixes():
            if row.get('fix_id') == fix_id:
                continue
            if error_type and row.get('error_type') and row.get('error_type') != error_type:
                continue
            score = 0.7 * _similarity(error_signature, str(row.get('error_signature', ''))) + 0.3 * _similarity(solution, str(row.get('solution', '')))
            if score > best_score:
                best_score = score
                best_id = str(row.get('fix_id'))
        if best_id is None:
            return NoveltyDecision(fix_id=fix_id, novelty_score=1.0, decision='novel', reason='No prior fixes found.')
        if best_score >= min_duplicate:
            return NoveltyDecision(
                fix_id=fix_id,
                novelty_score=round(1.0 - best_score, 4),
                decision='duplicate',
                duplicate_of=best_id,
                reason=f'High similarity to existing fix ({best_score:.2f}).',
            )
        if best_score >= min_variant:
            return NoveltyDecision(
                fix_id=fix_id,
                novelty_score=round(1.0 - best_score, 4),
                decision='variant',
                variant_of=best_id,
                reason=f'Moderate similarity to existing fix ({best_score:.2f}).',
            )
        return NoveltyDecision(
            fix_id=fix_id,
            novelty_score=round(1.0 - best_score, 4),
            decision='novel',
            reason=f'Nearest existing fix similarity below threshold ({best_score:.2f}).',
        )
