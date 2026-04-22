from __future__ import annotations

from typing import Any


class BluetoothScanner:
    def describe(self) -> dict[str, Any]:
        return {
            'scan_mode': 'trusted_device_summary',
            'supports': ['presence', 'rssi_summary', 'trusted_filtering'],
            'transport': 'mock_ble_scanner',
        }

    def signal_summary(self, devices: list[dict[str, Any]]) -> dict[str, Any]:
        visible = [d for d in devices if d.get('last_seen_rssi') is not None]
        return {
            'status': 'ok',
            'visible_count': len(visible),
            'trusted_visible_count': sum(1 for d in visible if d.get('trusted')),
            'devices': visible,
        }
