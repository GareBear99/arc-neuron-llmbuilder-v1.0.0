from __future__ import annotations

from fastapi import HTTPException


def raise_http_error_if(condition: bool, *, status_code: int, detail: dict) -> None:
    if condition:
        raise HTTPException(status_code=status_code, detail=detail)


def raise_http_error_unless_ok(result: dict, *, status_code: int = 404) -> dict:
    if not result.get("ok"):
        raise HTTPException(status_code=status_code, detail=result)
    return result
