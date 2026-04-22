from __future__ import annotations
from typing import Any
from .actions import MockDogBodyAdapter, MockTentacleArmAdapter
from .safety import SafetyInterlockEngine
from .schemas import RobotActionRequest, RobotState
class RoboticsGateway:
    def __init__(self)->None:
        self.safety=SafetyInterlockEngine(); self.adapters={'dog_body':MockDogBodyAdapter(),'tentacle_arm':MockTentacleArmAdapter()}
    def describe(self)->dict[str,Any]: return {'status':'ok','required':False,'doctrine':'bounded executive-layer bridge over deterministic body controllers','adapters':{n:a.describe() for n,a in self.adapters.items()}}
    def state_template(self)->dict[str,Any]: return {'status':'ok','state_template':RobotState().to_dict()}
    def safety_check(self,state:dict[str,Any],action:str,subsystem:str='dog_body',params:dict[str,Any]|None=None)->dict[str,Any]: return self.safety.evaluate(RobotState(**state),RobotActionRequest(action=action,subsystem=subsystem,params=params or {}))
    def perform(self,state:dict[str,Any],action:str,subsystem:str='dog_body',params:dict[str,Any]|None=None)->dict[str,Any]:
        request=RobotActionRequest(action=action,subsystem=subsystem,params=params or {})
        verdict=self.safety.evaluate(RobotState(**state),request)
        if not verdict['allowed']: return verdict
        return {'status':'ok','safety':verdict,'receipt':self.adapters[subsystem].perform(request).to_dict()}
