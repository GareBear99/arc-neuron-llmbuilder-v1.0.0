from __future__ import annotations
from typing import Any
from .schemas import MappingState
class MappingEngine:
    def describe(self)->dict[str,Any]: return {'status':'ok','required':False,'grid_values':{-1:'unknown',0:'free',1:'blocked'},'doctrine':'optional local occupancy-grid under the executive shell'}
    def state_template(self)->dict[str,Any]: return {'status':'ok','mapping_state':MappingState().to_dict()}
    def ingest_update(self,state:dict[str,Any],updates:list[dict[str,int]],robot_position:list[int]|None=None)->dict[str,Any]:
        model=MappingState(**state)
        for u in updates:
            x=int(u['x']); y=int(u['y'])
            if 0<=y<model.height and 0<=x<model.width: model.grid[y][x]=int(u['value'])
        if robot_position is not None: model.robot_position=[int(robot_position[0]),int(robot_position[1])]
        return {'status':'ok','mapping_state':model.to_dict(),'coverage':self.coverage(model.to_dict())['coverage']}
    def coverage(self,state:dict[str,Any])->dict[str,Any]:
        model=MappingState(**state); flat=[c for r in model.grid for c in r]; total=len(flat) or 1; explored=sum(1 for c in flat if c!=-1); free=sum(1 for c in flat if c==0); blocked=sum(1 for c in flat if c==1)
        return {'status':'ok','coverage':{'total_cells':total,'explored_cells':explored,'free_cells':free,'blocked_cells':blocked,'explored_ratio':round(explored/total,4)}}
