from __future__ import annotations

"""Continuation manager records degraded execution state so tasks can finish with receipts."""

from dataclasses import dataclass


@dataclass(slots=True)
class ContinuationRecord:
    task_kind: str
    mode: str
    reason: str
    final_status: str

    def to_dict(self) -> dict[str, str]:
        return {'task_kind': self.task_kind, 'mode': self.mode, 'reason': self.reason, 'final_status': self.final_status}


class ContinuationManager:
    def start(self, task_kind: str, mode: str, reason: str) -> ContinuationRecord:
        return ContinuationRecord(task_kind=task_kind, mode=mode, reason=reason, final_status='running')

    def finish(self, record: ContinuationRecord, final_status: str) -> ContinuationRecord:
        record.final_status = final_status
        return record
