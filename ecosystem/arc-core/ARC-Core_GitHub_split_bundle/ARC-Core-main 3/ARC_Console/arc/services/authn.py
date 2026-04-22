from __future__ import annotations
import secrets
from datetime import datetime, timedelta, timezone
from arc.core.auth import make_password_hash, verify_password
from arc.core.config import AUTH_BOOTSTRAP_PASSWORD, SESSION_TTL_HOURS
from arc.core.db import connect
from arc.core.schemas import LoginIn, new_id, utcnow
from arc.services.audit import append_receipt, log


def _expires_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()


def ensure_bootstrap_admin() -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM auth_users WHERE username = 'admin' LIMIT 1").fetchone()
        if row:
            return {"username": row["username"], "role": row["role"], "display_name": row["display_name"]}
        salt, hashed = make_password_hash(AUTH_BOOTSTRAP_PASSWORD)
        user_id = new_id("usr")
        now = utcnow()
        conn.execute(
            "INSERT INTO auth_users (user_id, username, display_name, role, password_salt, password_hash, is_active, created_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)",
            (user_id, "admin", "ARC Admin", "admin", salt, hashed, now),
        )
        conn.commit()
    append_receipt("auth_user", user_id, "admin", {"username": "admin", "role": "admin"})
    return {"username": "admin", "role": "admin", "display_name": "ARC Admin"}


def login(payload: LoginIn) -> dict:
    ensure_bootstrap_admin()
    with connect() as conn:
        row = conn.execute("SELECT * FROM auth_users WHERE username = ?", (payload.username,)).fetchone()
        if not row or not row["is_active"]:
            raise ValueError("Invalid credentials")
        if not verify_password(payload.password, row["password_salt"], row["password_hash"]):
            raise ValueError("Invalid credentials")
        session_id = new_id("sess")
        token = secrets.token_urlsafe(32)
        issued_at = utcnow()
        expires_at = _expires_at()
        conn.execute(
            "INSERT INTO auth_sessions (session_id, user_id, role, issued_at, expires_at, session_token, created_from, is_revoked) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            (session_id, row["user_id"], row["role"], issued_at, expires_at, token, payload.source),
        )
        conn.execute("UPDATE auth_users SET last_login_at = ? WHERE user_id = ?", (issued_at, row["user_id"]))
        conn.commit()
    log(row["role"], "login", row["username"], {"source": payload.source})
    append_receipt("auth_session", session_id, row["role"], {"username": row["username"], "source": payload.source})
    return {
        "session_id": session_id,
        "token": token,
        "role": row["role"],
        "username": row["username"],
        "display_name": row["display_name"],
        "issued_at": issued_at,
        "expires_at": expires_at,
        "bootstrap_password_hint": "Change ARC_BOOTSTRAP_PASSWORD in production" if payload.username == "admin" and payload.password == AUTH_BOOTSTRAP_PASSWORD else None,
    }


def resolve_session(token: str | None) -> dict | None:
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT s.*, u.username, u.display_name FROM auth_sessions s JOIN auth_users u ON u.user_id = s.user_id WHERE s.session_token = ?",
            (token,),
        ).fetchone()
    if not row or row["is_revoked"]:
        return None
    if row["expires_at"] <= utcnow():
        return None
    return dict(row)
