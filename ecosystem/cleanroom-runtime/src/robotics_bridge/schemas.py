from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(slots=True)
class RobotState:
    battery_pct: float = 100.0
    localization_confidence: float = 1.0
    nearest_obstacle_m: float = 9.99
    thermal_fault: bool = False
    motor_fault: bool = False
    estop_engaged: bool = False
    human_near_face_zone: bool = False
    locomotion_state: str = 'idle'
    arm_state: str = 'parked'
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(slots=True)
class RobotActionRequest:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    subsystem: str = 'dog_body'
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(slots=True)
class ActionReceipt:
    status: str
    action: str
    subsystem: str
    reason: str = ''
    params: dict[str, Any] = field(default_factory=dict)
    translated_command: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: return asdict(self)
