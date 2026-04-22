from __future__ import annotations
from typing import Any
from .actions import ARM_ACTIONS, DOG_ACTIONS
from .schemas import RobotActionRequest, RobotState
class SafetyInterlockEngine:
    def evaluate(self,state:RobotState,request:RobotActionRequest)->dict[str,Any]:
        denied=[]; warnings=[]
        if state.estop_engaged: denied.append('estop engaged')
        if state.battery_pct < 5.0 and request.action != 'dock': denied.append('battery critically low; only dock is allowed')
        elif state.battery_pct < 15.0 and request.action not in {'dock','halt','sit','brace'}: warnings.append('battery low; prefer docking or safe posture')
        if state.localization_confidence < 0.35 and request.action in {'walk_to_relative','turn'}: denied.append('localization confidence below motion threshold')
        if state.nearest_obstacle_m < 0.4 and request.action in {'walk_to_relative','turn'}: denied.append('near obstacle blocks locomotion action')
        if state.thermal_fault or state.motor_fault: denied.append('thermal or motor fault active')
        if state.human_near_face_zone and request.action in {'arm_point','arm_pick','arm_place','arm_soft_probe'}: denied.append('human near face zone blocks arm motion')
        if state.locomotion_state == 'moving' and request.action in ARM_ACTIONS: denied.append('arm actions blocked while locomotion is moving')
        if request.action not in sorted(DOG_ACTIONS|ARM_ACTIONS): denied.append(f'unknown bounded action: {request.action}')
        return {'status':'ok' if not denied else 'denied','allowed':not denied,'action':request.action,'subsystem':request.subsystem,'warnings':warnings,'reasons':denied,'state':state.to_dict(),'request':request.to_dict()}
