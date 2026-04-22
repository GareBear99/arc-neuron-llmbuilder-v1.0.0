from __future__ import annotations

from typing import Any

from .schemas import BluetoothDeviceRecord


class TrustedDeviceRegistry:
    def template(self) -> dict[str, Any]:
        return {
            'status': 'ok',
            'trusted_devices': [],
            'device_template': BluetoothDeviceRecord(
                device_id='device.example',
                display_name='Example BLE Device',
                profile='beacon_profile',
            ).to_dict(),
        }

    def register(self, devices: list[dict[str, Any]], device: dict[str, Any]) -> dict[str, Any]:
        record = BluetoothDeviceRecord(**device)
        updated = [item for item in devices if item.get('device_id') != record.device_id]
        updated.append(record.to_dict())
        return {'status': 'ok', 'trusted_devices': updated, 'registered_device': record.to_dict()}

    def find(self, devices: list[dict[str, Any]], device_id: str) -> dict[str, Any] | None:
        for item in devices:
            if item.get('device_id') == device_id:
                return item
        return None
