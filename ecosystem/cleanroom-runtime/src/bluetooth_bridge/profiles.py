from __future__ import annotations

from typing import Any


PROFILE_MATRIX: dict[str, dict[str, Any]] = {
    'beacon_profile': {
        'description': 'Presence beacon and nearby-asset profile.',
        'allowed_actions': ['read_status', 'emit_beacon'],
    },
    'garage_relay_profile': {
        'description': 'Authorized garage relay opener profile.',
        'allowed_actions': ['read_status', 'open', 'close', 'pulse'],
    },
    'sensor_tag_profile': {
        'description': 'Read-only sensor tag telemetry profile.',
        'allowed_actions': ['read_status', 'read_telemetry'],
    },
    'vehicle_telemetry_profile': {
        'description': 'Authorized vehicle telemetry and auxiliary command profile.',
        'allowed_actions': ['read_status', 'read_telemetry', 'locate'],
    },
    'door_lock_profile': {
        'description': 'Trusted lock profile with explicit policy gating.',
        'allowed_actions': ['read_status', 'lock', 'unlock'],
    },
}


def describe_profiles() -> dict[str, Any]:
    return PROFILE_MATRIX


def action_allowed(profile: str, action: str) -> bool:
    return action in PROFILE_MATRIX.get(profile, {}).get('allowed_actions', [])
