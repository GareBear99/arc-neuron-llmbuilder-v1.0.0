from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class BluetoothDeviceRecord:
    device_id: str
    display_name: str
    profile: str
    trusted: bool = False
    pairing_state: str = 'unpaired'
    ownership: str = 'unknown'
    signal_kind: str = 'ble'
    last_seen_rssi: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BluetoothActionRequest:
    action: str
    device_id: str | None = None
    profile: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BluetoothSignalBeacon:
    node_id: str = 'lucifer_node'
    role: str = 'operator_runtime'
    state: str = 'ready'
    signed: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BluetoothActionReceipt:
    status: str
    action: str
    reason: str = ''
    device_id: str | None = None
    profile: str | None = None
    translated_operation: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
