from __future__ import annotations

from typing import Any

from .profiles import action_allowed


class BluetoothSafetyEngine:
    def evaluate(self, devices: list[dict[str, Any]], request: dict[str, Any], operator_approved: bool = False) -> dict[str, Any]:
        action = request.get('action', '')
        device_id = request.get('device_id')
        profile = request.get('profile')
        params = request.get('params', {})
        dangerous_actions = {'unlock', 'open', 'close', 'pulse'}

        if action in {'advertise_start', 'advertise_stop', 'peripheral_start', 'peripheral_stop', 'signal_summary'}:
            return {'status': 'ok', 'allowed': True, 'reason': 'local_bluetooth_signal_action_allowed', 'request': request}

        target = next((item for item in devices if item.get('device_id') == device_id), None)
        if target is None:
            return {'status': 'denied', 'allowed': False, 'reason': 'unknown_device', 'request': request}
        if not bool(target.get('trusted')):
            return {'status': 'denied', 'allowed': False, 'reason': 'device_not_trusted', 'request': request, 'device': target}

        effective_profile = profile or target.get('profile')
        if not effective_profile:
            return {'status': 'denied', 'allowed': False, 'reason': 'missing_profile', 'request': request, 'device': target}
        if not action_allowed(effective_profile, action):
            return {'status': 'denied', 'allowed': False, 'reason': 'action_not_allowed_for_profile', 'request': request, 'device': target, 'profile': effective_profile}

        if action in dangerous_actions and not operator_approved:
            return {'status': 'denied', 'allowed': False, 'reason': 'operator_approval_required', 'request': request, 'device': target, 'profile': effective_profile}

        if params.get('requires_local_presence') and target.get('last_seen_rssi') is not None and int(target['last_seen_rssi']) < -90:
            return {'status': 'denied', 'allowed': False, 'reason': 'signal_too_weak_for_local_presence', 'request': request, 'device': target, 'profile': effective_profile}

        return {'status': 'ok', 'allowed': True, 'reason': 'trusted_profile_action_allowed', 'request': request, 'device': target, 'profile': effective_profile}
