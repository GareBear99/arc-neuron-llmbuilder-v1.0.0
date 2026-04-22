from __future__ import annotations

"""Retention policy for live, warm, and archived memory tiers.

This policy supports both normal age-based archival and the mirror-then-retire
mode where an item can be merged into archive early while remaining live in
front memory until its scheduled retirement date.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .records import MemoryRecord, parse_iso8601


@dataclass(slots=True)
class RetentionConfig:
    hot_days: int = 30
    warm_days: int = 180
    access_grace_days: int = 45

    @property
    def archive_after_days(self) -> int:
        return self.warm_days


class RetentionPolicy:
    def __init__(self, config: RetentionConfig | None = None) -> None:
        self.config = config or RetentionConfig()

    def tier_for(self, record: MemoryRecord, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        if not record.is_live_in_front_memory:
            return 'archive'
        created_at = parse_iso8601(record.created_at)
        scheduled_archive_at = parse_iso8601(record.scheduled_archive_at) if record.scheduled_archive_at else None
        if record.retention_mode == 'mirror_then_retire' and scheduled_archive_at is not None and now >= scheduled_archive_at:
            return 'archive'
        age_days = (now - created_at).days
        if age_days <= self.config.hot_days:
            return 'hot'
        if self._recently_accessed(record, now):
            return 'warm'
        if age_days <= self.config.warm_days or record.pinned:
            return 'warm'
        # Mirror-then-retire records stay warm/live until their scheduled cutoff.
        if record.retention_mode == 'mirror_then_retire':
            return 'warm'
        return 'archive'

    def should_archive(self, record: MemoryRecord, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if record.pinned or not record.is_live_in_front_memory:
            return False
        scheduled_archive_at = parse_iso8601(record.scheduled_archive_at) if record.scheduled_archive_at else None
        if record.retention_mode == 'mirror_then_retire' and scheduled_archive_at is not None and now >= scheduled_archive_at:
            return True
        if self._recently_accessed(record, now):
            return False
        return self.tier_for(record, now) == 'archive'

    def should_sync_archive(self, record: MemoryRecord, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if not record.is_live_in_front_memory:
            return False
        if record.retention_mode != 'mirror_then_retire' or not record.is_present_in_archive_branch:
            return False
        if record.archive_sync_last_at is None:
            return True
        last_sync = parse_iso8601(record.archive_sync_last_at)
        return last_sync < now

    def _recently_accessed(self, record: MemoryRecord, now: datetime) -> bool:
        if not record.last_accessed_at:
            return False
        last_accessed = parse_iso8601(record.last_accessed_at)
        return now - last_accessed <= timedelta(days=self.config.access_grace_days)
