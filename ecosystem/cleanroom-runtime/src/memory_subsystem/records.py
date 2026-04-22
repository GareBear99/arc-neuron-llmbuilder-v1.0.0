from __future__ import annotations

"""Readable, retention-aware memory records derived from canonical kernel events.

The memory layer keeps a machine-safe canonical form while also exposing a more
human-readable header (title/summary/keywords/category). This lets memory stack
cleanly over time while still carrying retention and archive lineage metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from arc_kernel.schemas import Event


def parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _default_title(event: Event) -> str:
    explicit = event.payload.get('memory_title')
    if explicit:
        return str(explicit)
    if 'text' in event.payload and str(event.payload['text']).strip():
        return str(event.payload['text']).strip().splitlines()[0][:80]
    if 'path' in event.payload:
        return f"{event.kind.value}:{event.payload['path']}"
    return f"{event.kind.value}:{event.event_id[:8]}"


def _default_summary(event: Event) -> str:
    explicit = event.payload.get('memory_summary')
    if explicit:
        return str(explicit)
    for key in ('text', 'content', 'reason', 'summary'):
        value = event.payload.get(key)
        if value:
            return ' '.join(str(value).split())[:240]
    return f"{event.kind.value} recorded by {event.actor}"


def _default_keywords(event: Event) -> List[str]:
    explicit = event.payload.get('memory_keywords')
    if isinstance(explicit, list):
        return [str(item) for item in explicit[:12]]
    candidates: List[str] = [event.kind.value]
    if 'path' in event.payload:
        candidates.append(PathLike.safe_name(event.payload['path']))
    text = str(event.payload.get('text', ''))
    for token in text.replace('::', ' ').replace('/', ' ').replace('_', ' ').split():
        cleaned = ''.join(ch for ch in token.lower() if ch.isalnum() or ch in {'-', '.'})
        if len(cleaned) >= 4 and cleaned not in candidates:
            candidates.append(cleaned)
        if len(candidates) >= 8:
            break
    return candidates


class PathLike:
    @staticmethod
    def safe_name(value: Any) -> str:
        raw = str(value).strip().replace('\\', '/').split('/')[-1]
        return raw[:80] or 'unknown'


@dataclass(slots=True)
class MemoryRecord:
    event_id: str
    kind: str
    actor: str
    created_at: str
    payload: Dict[str, Any]
    parent_event_id: Optional[str] = None
    pinned: bool = False
    last_accessed_at: Optional[str] = None
    title: str = ''
    summary: str = ''
    keywords: List[str] = field(default_factory=list)
    category: str = 'general'
    importance: str = 'normal'
    status: str = 'live'
    scheduled_archive_at: Optional[str] = None
    early_archive_merged_at: Optional[str] = None
    front_memory_retired_at: Optional[str] = None
    archive_sync_last_at: Optional[str] = None
    archived_early: bool = False
    archive_reason: Optional[str] = None
    source_tier: str = 'front_memory'
    archive_branch_id: Optional[str] = None
    archive_pack_id: Optional[str] = None
    is_live_in_front_memory: bool = True
    is_present_in_archive_branch: bool = False
    retention_mode: str = 'standard'

    @classmethod
    def from_event(cls, event: Event, status: Optional[Dict[str, Any]] = None, default_archive_after_days: int = 180) -> "MemoryRecord":
        status = status or {}
        pinned = bool(event.payload.get('memory_pinned', False))
        last_accessed_at = event.payload.get('last_accessed_at')
        created_dt = parse_iso8601(event.created_at)
        scheduled_archive_at = status.get('scheduled_archive_at') or event.payload.get('scheduled_archive_at')
        if not scheduled_archive_at:
            scheduled_archive_at = (created_dt + timedelta(days=default_archive_after_days)).isoformat()
        early_archive_merged_at = status.get('early_archive_merged_at')
        front_memory_retired_at = status.get('front_memory_retired_at')
        archive_sync_last_at = status.get('archive_sync_last_at')
        retention_mode = status.get('retention_mode') or event.payload.get('retention_mode', 'standard')
        is_present_in_archive_branch = bool(status.get('is_present_in_archive_branch', False))
        is_live_in_front_memory = not bool(front_memory_retired_at)
        if is_live_in_front_memory and is_present_in_archive_branch:
            lifecycle_status = 'live_and_archived'
        elif is_live_in_front_memory:
            lifecycle_status = 'live'
        else:
            lifecycle_status = 'archived'
        return cls(
            event_id=event.event_id,
            kind=event.kind.value,
            actor=event.actor,
            created_at=event.created_at,
            payload=dict(event.payload),
            parent_event_id=event.parent_event_id,
            pinned=pinned,
            last_accessed_at=last_accessed_at,
            title=_default_title(event),
            summary=_default_summary(event),
            keywords=_default_keywords(event),
            category=str(event.payload.get('memory_category', event.kind.value)),
            importance=str(event.payload.get('memory_importance', 'normal')),
            status=lifecycle_status,
            scheduled_archive_at=scheduled_archive_at,
            early_archive_merged_at=early_archive_merged_at,
            front_memory_retired_at=front_memory_retired_at,
            archive_sync_last_at=archive_sync_last_at,
            archived_early=bool(status.get('archived_early', False)),
            archive_reason=status.get('archive_reason'),
            source_tier=str(status.get('source_tier', 'front_memory')),
            archive_branch_id=status.get('archive_branch_id'),
            archive_pack_id=status.get('archive_pack_id'),
            is_live_in_front_memory=is_live_in_front_memory,
            is_present_in_archive_branch=is_present_in_archive_branch,
            retention_mode=retention_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'kind': self.kind,
            'actor': self.actor,
            'created_at': self.created_at,
            'payload': self.payload,
            'parent_event_id': self.parent_event_id,
            'pinned': self.pinned,
            'last_accessed_at': self.last_accessed_at,
            'title': self.title,
            'summary': self.summary,
            'keywords': self.keywords,
            'category': self.category,
            'importance': self.importance,
            'status': self.status,
            'scheduled_archive_at': self.scheduled_archive_at,
            'early_archive_merged_at': self.early_archive_merged_at,
            'front_memory_retired_at': self.front_memory_retired_at,
            'archive_sync_last_at': self.archive_sync_last_at,
            'archived_early': self.archived_early,
            'archive_reason': self.archive_reason,
            'source_tier': self.source_tier,
            'archive_branch_id': self.archive_branch_id,
            'archive_pack_id': self.archive_pack_id,
            'is_live_in_front_memory': self.is_live_in_front_memory,
            'is_present_in_archive_branch': self.is_present_in_archive_branch,
            'retention_mode': self.retention_mode,
        }
