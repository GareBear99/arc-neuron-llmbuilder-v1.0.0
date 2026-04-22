from __future__ import annotations
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow

STATUS_ORDER = {"offline": 0, "degraded": 1, "healthy": 2}


def register_provider(name: str, provider_type: str, enabled: bool = True, local_only: bool = False, notes: str = "") -> dict:
    """Register a new provider in the provider registry."""
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO provider_registry (provider_name, provider_type, enabled, local_only, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_name) DO UPDATE SET
                provider_type=excluded.provider_type,
                enabled=excluded.enabled,
                local_only=excluded.local_only,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (name, provider_type, 1 if enabled else 0, 1 if local_only else 0, notes, now, now),
        )
        conn.commit()
    return {"ok": True, "provider_name": name, "provider_type": provider_type, "enabled": enabled, "local_only": local_only}


def set_provider_health(provider_name: str, status: str, latency_ms: int | None = None, error_rate: float | None = None, notes: str = "") -> dict:
    """Record a health snapshot for a provider."""
    if status not in STATUS_ORDER:
        return {"ok": False, "error": "invalid_status", "allowed": list(STATUS_ORDER.keys())}
    health_id = f"hlth_{uuid.uuid4().hex[:12]}"
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO provider_health (health_id, provider_name, status, latency_ms, error_rate, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (health_id, provider_name, status, latency_ms, error_rate, notes, now),
        )
        conn.commit()
    return {"ok": True, "health_id": health_id, "provider_name": provider_name, "status": status}


def get_provider_record(provider_name: str) -> dict | None:
    """Return the provider registry record for a named provider, or None if not registered."""
    with connect() as conn:
        row = conn.execute(
            "SELECT provider_name, provider_type, enabled, local_only, notes, created_at, updated_at FROM provider_registry WHERE provider_name = ?",
            (provider_name,),
        ).fetchone()
    return dict(row) if row else None


def get_latest_provider_health(provider_name: str) -> dict | None:
    """Return the most recent health snapshot for a named provider, or None."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT provider_name, status, latency_ms, error_rate, notes, created_at
            FROM provider_health WHERE provider_name = ? ORDER BY created_at DESC LIMIT 1
            """,
            (provider_name,),
        ).fetchone()
    return dict(row) if row else None


def list_providers(provider_type: str | None = None) -> dict:
    """List registered providers, optionally filtered by provider_type."""
    q = "SELECT provider_name, provider_type, enabled, local_only, notes, created_at, updated_at FROM provider_registry"
    params = []
    if provider_type:
        q += " WHERE provider_type = ?"
        params.append(provider_type)
    q += " ORDER BY provider_type, provider_name"
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for row in rows:
        row["health"] = get_latest_provider_health(row["provider_name"])
    return {"ok": True, "providers": rows}


def provider_is_usable(provider_name: str) -> dict:
    """Return True if a provider is registered, enabled, and not offline."""
    record = get_provider_record(provider_name)
    if not record:
        return {"ok": False, "usable": False, "reason": "provider_not_registered"}
    if not record["enabled"]:
        return {"ok": False, "usable": False, "reason": "provider_disabled", "provider": record}
    health = get_latest_provider_health(provider_name)
    if health and health["status"] == "offline":
        return {"ok": False, "usable": False, "reason": "provider_offline", "provider": record, "health": health}
    if health and health["status"] == "degraded":
        return {"ok": True, "usable": True, "reason": "provider_degraded", "provider": record, "health": health}
    return {"ok": True, "usable": True, "reason": "provider_healthy" if health else "provider_no_health_snapshot", "provider": record, "health": health}
