from __future__ import annotations
from typing import Any
from .mapper import MappingEngine
from .planner import GridPlanner
class MappingGateway:
    def __init__(self)->None: self.engine=MappingEngine(); self.planner=GridPlanner()
    def describe(self)->dict[str,Any]: payload=self.engine.describe(); payload['planner']='grid_bfs'; return payload
    def state_template(self)->dict[str,Any]: return self.engine.state_template()
    def coverage(self,state:dict[str,Any])->dict[str,Any]: return self.engine.coverage(state)
    def ingest_update(self,state:dict[str,Any],updates:list[dict[str,int]],robot_position:list[int]|None=None)->dict[str,Any]: return self.engine.ingest_update(state,updates,robot_position=robot_position)
    def plan_route(self,state:dict[str,Any],goal:list[int])->dict[str,Any]: return self.planner.plan_route(state,goal)
