from __future__ import annotations
import hashlib
import json
import re

def normalize_entity(text: str | None) -> str:
    if not text:
        return ""
    value = re.sub(r"\s+", " ", text.strip().lower())
    return value

def guess_entity_type(value: str) -> str:
    v = value.lower()
    if any(tok in v for tok in ["st", "ave", "road", "rd", "park", "mall", "airport"]):
        return "location"
    if any(ch.isdigit() for ch in v) and ("device" in v or "cam" in v or "node" in v):
        return "device"
    if "corp" in v or "inc" in v or "ltd" in v or "group" in v:
        return "org"
    return "person"

def fingerprint(event_type: str, source: str, subject: str, object_: str | None, location: str | None, payload: dict) -> str:
    blob = json.dumps({
        "event_type": event_type,
        "source": source,
        "subject": normalize_entity(subject),
        "object": normalize_entity(object_),
        "location": normalize_entity(location),
        "payload": payload,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]
