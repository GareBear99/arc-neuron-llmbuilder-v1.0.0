from __future__ import annotations

"""Retention manager for hot/warm/archive memory and archive mirroring.

The manager supports both normal age-based archival and a dual-presence mode
where a memory item is merged into the archive branch early but remains live in
front memory until its scheduled retirement date.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from arc_kernel.engine import KernelEngine
from arc_kernel.schemas import Event, EventKind

from .archive import ArchivePack
from .records import MemoryRecord, parse_iso8601
from .retention import RetentionConfig, RetentionPolicy


@dataclass(slots=True)
class ConsolidationResult:
    hot_count: int
    warm_count: int
    archived_count: int
    archive_path: str | None = None
    archived_event_ids: List[str] | None = None
    synced_event_ids: List[str] | None = None


class MemoryManager:
    def __init__(
        self,
        kernel: KernelEngine,
        storage_root: str | Path,
        config: RetentionConfig | None = None,
    ) -> None:
        self.kernel = kernel
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.config = config or RetentionConfig()
        self.policy = RetentionPolicy(self.config)
        self.archive_dir = self.storage_root / 'archive'
        self.warm_dir = self.storage_root / 'warm'
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.warm_dir.mkdir(parents=True, exist_ok=True)

    def consolidate(self, now: datetime | None = None) -> ConsolidationResult:
        now = now or datetime.now(timezone.utc)
        records = self._memory_records(now)
        hot_records: list[MemoryRecord] = []
        warm_records: list[MemoryRecord] = []
        archive_records: list[MemoryRecord] = []
        synced_event_ids: list[str] = []
        for record in records:
            if self.policy.should_sync_archive(record, now):
                self._sync_live_record(record, now, reason='scheduled_sync')
                synced_event_ids.append(record.event_id)
            tier = self.policy.tier_for(record, now)
            if tier == 'hot':
                hot_records.append(record)
            elif tier == 'warm':
                warm_records.append(record)
            elif self.policy.should_archive(record, now):
                archive_records.append(record)
            else:
                warm_records.append(record)
        self._write_warm_index(warm_records)
        archive_path = None
        archived_event_ids: List[str] = []
        if archive_records:
            pack = ArchivePack.create(
                self.archive_dir,
                archive_records,
                manifest_extras={
                    'kind': 'retirement_archive',
                    'retired_event_ids': [record.event_id for record in archive_records],
                },
            )
            archive_path = str(pack.archive_path)
            archived_event_ids = list(pack.manifest['event_ids'])
            for record in archive_records:
                self.kernel.record_memory_update(
                    actor='memory-manager',
                    payload={
                        'kind': 'archive_retired',
                        'target_event_id': record.event_id,
                        'scheduled_archive_at': record.scheduled_archive_at,
                        'front_memory_retired_at': now.isoformat(),
                        'archive_branch_id': record.archive_branch_id or 'archive_branch_main',
                        'archive_pack_id': pack.archive_path.name,
                        'retention_mode': record.retention_mode,
                    },
                )
            self.kernel.record_memory_update(
                actor='memory-manager',
                payload={
                    'kind': 'archive_created',
                    'archive_path': archive_path,
                    'record_count': len(archive_records),
                    'event_ids': archived_event_ids,
                    'config': {
                        'hot_days': self.config.hot_days,
                        'warm_days': self.config.warm_days,
                        'access_grace_days': self.config.access_grace_days,
                    },
                },
            )
        return ConsolidationResult(
            hot_count=len(hot_records),
            warm_count=len(warm_records),
            archived_count=len(archive_records),
            archive_path=archive_path,
            archived_event_ids=archived_event_ids,
            synced_event_ids=synced_event_ids,
        )

    def archive_now_but_keep_live(
        self,
        event_id: str,
        *,
        reason: str = 'manual_override',
        archive_branch_id: str = 'archive_branch_main',
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        source_event = self.kernel.log.find_by_event_id(event_id)
        if source_event is None:
            raise ValueError(f'unknown memory event_id: {event_id}')
        status_map = self._status_by_event_id()
        record = MemoryRecord.from_event(source_event, status=status_map.get(event_id), default_archive_after_days=self.config.archive_after_days)
        if not record.is_present_in_archive_branch:
            pack_name = f'mirror_{event_id[:8]}_{now.strftime("%Y%m%dT%H%M%S")}.arcpack'
            pack = ArchivePack.create(
                self.archive_dir,
                [record],
                pack_name=pack_name,
                manifest_extras={
                    'kind': 'early_mirror',
                    'archive_branch_id': archive_branch_id,
                    'mirror_created_at': now.isoformat(),
                    'retention_mode': 'mirror_then_retire',
                },
            )
            archive_pack_id = pack.archive_path.name
        else:
            archive_pack_id = record.archive_pack_id
        payload = {
            'kind': 'archive_mirrored',
            'target_event_id': event_id,
            'scheduled_archive_at': record.scheduled_archive_at,
            'early_archive_merged_at': now.isoformat(),
            'archive_sync_last_at': now.isoformat(),
            'archived_early': True,
            'archive_reason': reason,
            'source_tier': 'front_memory',
            'archive_branch_id': archive_branch_id,
            'archive_pack_id': archive_pack_id,
            'is_live_in_front_memory': True,
            'is_present_in_archive_branch': True,
            'retention_mode': 'mirror_then_retire',
            'title': record.title,
            'summary': record.summary,
            'keywords': record.keywords,
        }
        self.kernel.record_memory_update(actor='memory-manager', payload=payload)
        return {'status': 'ok', 'event_id': event_id, 'archive_pack_id': archive_pack_id, 'archive_branch_id': archive_branch_id, 'scheduled_archive_at': record.scheduled_archive_at, 'early_archive_merged_at': payload['early_archive_merged_at'], 'retention_mode': 'mirror_then_retire'}

    def sync_live_mirrors(self, event_id: str | None = None, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        records = self._memory_records(now)
        synced: list[str] = []
        for record in records:
            if event_id and record.event_id != event_id:
                continue
            if self.policy.should_sync_archive(record, now):
                self._sync_live_record(record, now, reason='manual_sync' if event_id else 'bulk_sync')
                synced.append(record.event_id)
        return {'status': 'ok', 'synced_event_ids': synced, 'sync_count': len(synced), 'synced_at': now.isoformat()}


    def memory_status(self, now: datetime | None = None) -> Dict[str, Any]:
        """Return readable memory-tier status plus archive lineage metadata."""
        now = now or datetime.now(timezone.utc)
        records = self._memory_records(now)
        tiers = {'hot': [], 'warm': [], 'archive': []}
        for record in records:
            tiers[self.policy.tier_for(record, now)].append(record.to_dict())
        return {
            'status': 'ok',
            'counts': {name: len(rows) for name, rows in tiers.items()},
            'records': tiers,
            'archive_manifests': self.archive_manifest_index(),
        }

    def search_memory(self, query: str, *, now: datetime | None = None, limit: int = 10) -> Dict[str, Any]:
        """Search live/warm/archive memory using readable SEO-like headers."""
        now = now or datetime.now(timezone.utc)
        query_terms = [term.lower() for term in query.split() if term.strip()]
        results: list[dict[str, Any]] = []
        source_map: dict[str, dict[str, Any]] = {}
        for record in self._memory_records(now):
            entry = record.to_dict()
            entry['tier'] = self.policy.tier_for(record, now)
            entry['source'] = 'live'
            source_map[record.event_id] = entry
        for entry in source_map.values():
            entry['score'] = self._score_memory_entry(entry, query_terms)
            if entry['score'] > 0:
                results.append(entry)
        for pack in self.list_archives():
            for row in pack.load_records():
                event_id = row.get('event_id')
                if event_id in source_map:
                    continue
                entry = dict(row)
                entry['tier'] = 'archive'
                entry['source'] = 'archive'
                entry['archive_pack_id'] = pack.archive_path.name
                entry['score'] = self._score_memory_entry(entry, query_terms)
                if entry['score'] > 0:
                    results.append(entry)
        results.sort(key=lambda row: (-float(row.get('score', 0.0)), str(row.get('status', '')), str(row.get('title', ''))))
        return {'status': 'ok', 'query': query, 'result_count': len(results[:limit]), 'results': results[:limit]}

    def _score_memory_entry(self, entry: Dict[str, Any], query_terms: List[str]) -> float:
        if not query_terms:
            return 0.0
        title = str(entry.get('title', '')).lower()
        summary = str(entry.get('summary', '')).lower()
        keywords = [str(value).lower() for value in entry.get('keywords', [])]
        category = str(entry.get('category', '')).lower()
        importance = str(entry.get('importance', 'normal')).lower()
        status = str(entry.get('status', '')).lower()
        score = 0.0
        for term in query_terms:
            if term in title:
                score += 4.0
            if term in summary:
                score += 2.5
            if any(term in keyword for keyword in keywords):
                score += 3.0
            if term in category:
                score += 1.5
            if term == status:
                score += 0.5
        if importance == 'high':
            score += 1.0
        if status == 'live_and_archived':
            score += 0.75
        elif status == 'live':
            score += 0.5
        return score

    def list_archives(self) -> List[ArchivePack]:
        packs = []
        for path in sorted(self.archive_dir.glob('*.arcpack')):
            packs.append(ArchivePack.open(path))
        return packs

    def archive_manifest_index(self) -> List[Dict[str, Any]]:
        return [pack.manifest for pack in self.list_archives()]

    def retrieve_archived_event_ids(self, archive_name: str) -> List[str]:
        pack = ArchivePack.open(self.archive_dir / archive_name)
        return list(pack.manifest.get('event_ids', []))

    def _memory_records(self, now: datetime) -> List[MemoryRecord]:
        status_map = self._status_by_event_id()
        events = self.kernel.log.all()
        return [MemoryRecord.from_event(event, status=status_map.get(event.event_id), default_archive_after_days=self.config.archive_after_days) for event in events if event.kind != EventKind.MEMORY_UPDATE]

    def _status_by_event_id(self) -> Dict[str, Dict[str, Any]]:
        status: Dict[str, Dict[str, Any]] = {}
        for event in self.kernel.log.all():
            if event.kind != EventKind.MEMORY_UPDATE:
                continue
            target = event.payload.get('target_event_id')
            if not target:
                continue
            current = status.setdefault(target, {})
            kind = event.payload.get('kind')
            if kind == 'archive_mirrored':
                current.update({
                    'scheduled_archive_at': event.payload.get('scheduled_archive_at'),
                    'early_archive_merged_at': event.payload.get('early_archive_merged_at'),
                    'archive_sync_last_at': event.payload.get('archive_sync_last_at'),
                    'archived_early': bool(event.payload.get('archived_early', True)),
                    'archive_reason': event.payload.get('archive_reason'),
                    'source_tier': event.payload.get('source_tier', 'front_memory'),
                    'archive_branch_id': event.payload.get('archive_branch_id'),
                    'archive_pack_id': event.payload.get('archive_pack_id'),
                    'is_present_in_archive_branch': bool(event.payload.get('is_present_in_archive_branch', True)),
                    'retention_mode': event.payload.get('retention_mode', 'mirror_then_retire'),
                })
            elif kind == 'archive_sync':
                current.update({
                    'archive_sync_last_at': event.payload.get('archive_sync_last_at'),
                    'archive_pack_id': event.payload.get('archive_pack_id', current.get('archive_pack_id')),
                    'is_present_in_archive_branch': True,
                })
            elif kind == 'archive_retired':
                current.update({
                    'front_memory_retired_at': event.payload.get('front_memory_retired_at'),
                    'archive_pack_id': event.payload.get('archive_pack_id', current.get('archive_pack_id')),
                    'archive_branch_id': event.payload.get('archive_branch_id', current.get('archive_branch_id')),
                    'retention_mode': event.payload.get('retention_mode', current.get('retention_mode', 'standard')),
                    'is_present_in_archive_branch': True,
                })
        return status

    def _sync_live_record(self, record: MemoryRecord, now: datetime, *, reason: str) -> None:
        pack_name = f'sync_{record.event_id[:8]}_{now.strftime("%Y%m%dT%H%M%S")}.arcpack'
        pack = ArchivePack.create(
            self.archive_dir,
            [record],
            pack_name=pack_name,
            manifest_extras={
                'kind': 'live_sync',
                'archive_branch_id': record.archive_branch_id or 'archive_branch_main',
                'sync_reason': reason,
                'sync_created_at': now.isoformat(),
                'retention_mode': record.retention_mode,
            },
        )
        self.kernel.record_memory_update(
            actor='memory-manager',
            payload={
                'kind': 'archive_sync',
                'target_event_id': record.event_id,
                'archive_sync_last_at': now.isoformat(),
                'archive_branch_id': record.archive_branch_id or 'archive_branch_main',
                'archive_pack_id': pack.archive_path.name,
                'retention_mode': record.retention_mode,
                'sync_reason': reason,
            },
        )

    def _write_warm_index(self, warm_records: Iterable[MemoryRecord]) -> None:
        payload = [record.to_dict() for record in warm_records]
        target = self.warm_dir / 'warm_index.json'
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
