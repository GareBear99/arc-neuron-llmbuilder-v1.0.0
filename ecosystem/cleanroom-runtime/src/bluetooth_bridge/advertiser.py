from __future__ import annotations

from typing import Any

from .schemas import BluetoothActionReceipt, BluetoothSignalBeacon


class LocalSignalEmitter:
    def describe(self) -> dict[str, Any]:
        return {
            'advertising_supported': 'optional_platform_adapter',
            'peripheral_supported': 'optional_platform_adapter',
            'default_modes': ['beacon', 'gatt_service'],
        }

    def start_advertising(self, beacon: dict[str, Any] | None = None) -> BluetoothActionReceipt:
        payload = BluetoothSignalBeacon(**(beacon or {})).to_dict()
        return BluetoothActionReceipt(
            status='ok',
            action='advertise_start',
            reason='mock_advertising_started',
            translated_operation={'mode': 'beacon_advertising', 'payload': payload},
            response={'emitting': True, 'transport': 'mock_ble_advertiser'},
        )

    def stop_advertising(self) -> BluetoothActionReceipt:
        return BluetoothActionReceipt(
            status='ok',
            action='advertise_stop',
            reason='mock_advertising_stopped',
            translated_operation={'mode': 'beacon_advertising'},
            response={'emitting': False},
        )

    def start_peripheral(self, service_name: str = 'lucifer_status') -> BluetoothActionReceipt:
        return BluetoothActionReceipt(
            status='ok',
            action='peripheral_start',
            reason='mock_peripheral_started',
            translated_operation={'mode': 'gatt_peripheral', 'service_name': service_name},
            response={'serving': True, 'transport': 'mock_gatt_peripheral'},
        )

    def stop_peripheral(self) -> BluetoothActionReceipt:
        return BluetoothActionReceipt(
            status='ok',
            action='peripheral_stop',
            reason='mock_peripheral_stopped',
            translated_operation={'mode': 'gatt_peripheral'},
            response={'serving': False},
        )
