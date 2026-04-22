from __future__ import annotations

from typing import Any

from .advertiser import LocalSignalEmitter
from .profiles import describe_profiles
from .registry import TrustedDeviceRegistry
from .safety import BluetoothSafetyEngine
from .scanner import BluetoothScanner
from .schemas import BluetoothActionReceipt


class BluetoothGateway:
    def __init__(self) -> None:
        self.registry = TrustedDeviceRegistry()
        self.safety = BluetoothSafetyEngine()
        self.scanner = BluetoothScanner()
        self.emitter = LocalSignalEmitter()

    def describe(self) -> dict[str, Any]:
        return {
            'status': 'ok',
            'required': False,
            'doctrine': 'optional trusted-device bluetooth bridge with bounded profiles, receipts, and local signal generation',
            'profiles': describe_profiles(),
            'scanner': self.scanner.describe(),
            'emitter': self.emitter.describe(),
        }

    def device_template(self) -> dict[str, Any]:
        return self.registry.template()

    def register_device(self, devices: list[dict[str, Any]], device: dict[str, Any]) -> dict[str, Any]:
        return self.registry.register(devices, device)

    def trusted_list(self, devices: list[dict[str, Any]]) -> dict[str, Any]:
        return {'status': 'ok', 'trusted_devices': [d for d in devices if d.get('trusted')]}

    def inspect_device(self, devices: list[dict[str, Any]], device_id: str) -> dict[str, Any]:
        found = self.registry.find(devices, device_id)
        if found is None:
            return {'status': 'not_found', 'reason': 'device_not_found', 'device_id': device_id}
        return {'status': 'ok', 'device': found}

    def signal_summary(self, devices: list[dict[str, Any]]) -> dict[str, Any]:
        return self.scanner.signal_summary(devices)

    def signal_observation(self, devices: list[dict[str, Any]], device_id: str) -> dict[str, Any]:
        found = self.registry.find(devices, device_id)
        if found is None:
            return {'status': 'not_found', 'reason': 'device_not_found', 'device_id': device_id}
        observation = {
            'device_id': found.get('device_id'),
            'display_name': found.get('display_name'),
            'profile': found.get('profile'),
            'trusted': found.get('trusted', False),
            'pairing_state': found.get('pairing_state'),
            'ownership': found.get('ownership'),
            'signal_kind': found.get('signal_kind', 'ble'),
            'last_seen_rssi': found.get('last_seen_rssi'),
            'metadata': found.get('metadata', {}),
            'x_m': found.get('x_m', 0.0),
            'y_m': found.get('y_m', 0.0),
            'z_m': found.get('z_m', 0.0),
            'confidence': found.get('confidence'),
        }
        return {'status': 'ok', 'signal_observation': observation}

    def policy_check(self, devices: list[dict[str, Any]], action: str, device_id: str | None = None, profile: str | None = None, params: dict[str, Any] | None = None, operator_approved: bool = False) -> dict[str, Any]:
        return self.safety.evaluate(devices, {'action': action, 'device_id': device_id, 'profile': profile, 'params': params or {}}, operator_approved=operator_approved)

    def perform(self, devices: list[dict[str, Any]], action: str, device_id: str | None = None, profile: str | None = None, params: dict[str, Any] | None = None, operator_approved: bool = False) -> dict[str, Any]:
        params = params or {}
        verdict = self.policy_check(devices, action=action, device_id=device_id, profile=profile, params=params, operator_approved=operator_approved)
        if not verdict.get('allowed'):
            return verdict

        if action == 'advertise_start':
            receipt = self.emitter.start_advertising(params.get('beacon'))
        elif action == 'advertise_stop':
            receipt = self.emitter.stop_advertising()
        elif action == 'peripheral_start':
            receipt = self.emitter.start_peripheral(service_name=params.get('service_name', 'lucifer_status'))
        elif action == 'peripheral_stop':
            receipt = self.emitter.stop_peripheral()
        else:
            receipt = BluetoothActionReceipt(
                status='ok',
                action=action,
                reason='mock_trusted_device_action',
                device_id=device_id,
                profile=profile or verdict.get('profile'),
                translated_operation={'transport': 'mock_ble_client', 'action': action, 'params': params},
                response={'ack': True},
            )
        return {'status': 'ok', 'safety': verdict, 'receipt': receipt.to_dict()}
