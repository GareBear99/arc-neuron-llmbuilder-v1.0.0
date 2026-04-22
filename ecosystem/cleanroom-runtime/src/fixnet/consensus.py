from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ConsensusRecord, utcnow_iso


class FixConsensus:
    """Consensus/trust analytics for FixNet records.

    ARC-side equivalent of LuciferAI's ConsensusDictionary. This is intentionally
    read-only with respect to fix content: it stores only trust metadata.
    """

    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.fixnet_dir = self.runtime_root / '.arc_lucifer' / 'fixnet'
        self.fixnet_dir.mkdir(parents=True, exist_ok=True)
        self.consensus_path = self.fixnet_dir / 'consensus.json'
        if not self.consensus_path.exists():
            self.consensus_path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding='utf-8')

    def _load(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.consensus_path.read_text(encoding='utf-8'))

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.consensus_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def get(self, fix_id: str) -> dict[str, Any] | None:
        return self._load().get(fix_id)

    def upsert(self, record: ConsensusRecord) -> ConsensusRecord:
        data = self._load()
        record.updated_at = utcnow_iso()
        data[record.fix_id] = record.to_dict()
        self._save(data)
        return record

    def record_outcome(self, fix_id: str, *, succeeded: bool) -> ConsensusRecord:
        current = self.get(fix_id) or ConsensusRecord(fix_id=fix_id).to_dict()
        success_count = int(current.get('success_count', 0)) + (1 if succeeded else 0)
        failure_count = int(current.get('failure_count', 0)) + (0 if succeeded else 1)
        usage_count = int(current.get('usage_count', 0)) + 1
        total = success_count + failure_count
        success_rate = (success_count / total) if total else 0.0

        # Simple trust tiers matching LuciferAI docs philosophy.
        if success_rate >= 0.75 and usage_count >= 4:
            trust_level = 'highly_trusted'
            quarantined = False
        elif success_rate >= 0.51 and usage_count >= 2:
            trust_level = 'trusted'
            quarantined = False
        elif success_rate < 0.30 and usage_count >= 3:
            trust_level = 'quarantined'
            quarantined = True
        else:
            trust_level = 'experimental'
            quarantined = False

        record = ConsensusRecord(
            fix_id=fix_id,
            trust_level=trust_level,
            success_rate=round(success_rate, 4),
            usage_count=usage_count,
            success_count=success_count,
            failure_count=failure_count,
            reputation_score=float(current.get('reputation_score', 0.5)),
            quarantined=quarantined,
        )
        return self.upsert(record)

    def stats(self) -> dict[str, Any]:
        data = self._load()
        tiers: dict[str, int] = {}
        for row in data.values():
            tiers[row.get('trust_level', 'unknown')] = tiers.get(row.get('trust_level', 'unknown'), 0) + 1
        return {
            'fixes_scored': len(data),
            'tiers': dict(sorted(tiers.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
