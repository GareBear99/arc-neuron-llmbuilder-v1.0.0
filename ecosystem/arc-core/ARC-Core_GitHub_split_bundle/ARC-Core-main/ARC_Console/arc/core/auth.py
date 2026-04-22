from __future__ import annotations
from fastapi import Header, HTTPException
from arc.core.config import DEMO_MODE, SHARED_TOKEN

ROLE_ORDER = {"observer": 1, "analyst": 2, "operator": 3, "approver": 4, "admin": 5}


def require_role(required: str, x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> str:
    session_role = None
    if authorization and authorization.startswith("Bearer "):
        from arc.services.authn import resolve_session
        session = resolve_session(authorization.replace("Bearer ", "", 1))
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        session_role = session["role"]
    role = (session_role or x_arc_role or "observer").lower()
    if role not in ROLE_ORDER:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
    if ROLE_ORDER[role] < ROLE_ORDER[required]:
        raise HTTPException(status_code=403, detail=f"{required} role required")
    if session_role:
        return role
    if SHARED_TOKEN and required != "observer" and x_arc_token != SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="Valid X-ARC-Token required")
    if not DEMO_MODE and required == "observer" and role == "observer" and SHARED_TOKEN and x_arc_token != SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="Valid X-ARC-Token required")
    return role


def make_password_hash(password: str, salt: str | None = None) -> tuple[str, str]:
    import base64, hashlib, os
    raw_salt = salt.encode("utf-8") if salt else os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), raw_salt, 120_000)
    return base64.b64encode(raw_salt).decode("ascii"), base64.b64encode(derived).decode("ascii")


def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    import base64, hashlib, hmac
    salt = base64.b64decode(salt_b64.encode("ascii"))
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(base64.b64encode(candidate).decode("ascii"), hash_b64)
