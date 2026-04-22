from __future__ import annotations
from typing import Any
from .schemas import ActionReceipt, RobotActionRequest
DOG_ACTIONS={'stand','sit','halt','brace','dock','scan_posture','turn','walk_to_relative'}
ARM_ACTIONS={'arm_park','arm_ready','arm_retract','arm_point','arm_pick','arm_place','arm_soft_probe'}
class MockDogBodyAdapter:
    name='mock_dog_body'
    def describe(self)->dict[str,Any]: return {'name':self.name,'kind':'robot_dog','bounded_actions':sorted(DOG_ACTIONS),'required':False}
    def perform(self,request:RobotActionRequest)->ActionReceipt:
        translated={'driver':self.name,'verb':request.action,'pose_mode':request.params.get('pose_mode','default'),'params':dict(request.params)}
        return ActionReceipt(status='ok',action=request.action,subsystem=request.subsystem,reason='mock dog-body execution completed',params=dict(request.params),translated_command=translated)
class MockTentacleArmAdapter:
    name='mock_tentacle_arm'
    def describe(self)->dict[str,Any]: return {'name':self.name,'kind':'tentacle_arm','bounded_actions':sorted(ARM_ACTIONS),'required':False}
    def perform(self,request:RobotActionRequest)->ActionReceipt:
        translated={'driver':self.name,'verb':request.action,'compliance_mode':request.params.get('compliance_mode','safe'),'params':dict(request.params)}
        return ActionReceipt(status='ok',action=request.action,subsystem=request.subsystem,reason='mock tentacle-arm execution completed',params=dict(request.params),translated_command=translated)
