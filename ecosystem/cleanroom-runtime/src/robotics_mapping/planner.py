from __future__ import annotations
from collections import deque
from .schemas import MappingState, RoutePlan
class GridPlanner:
    def plan_route(self,state:dict[str,object],goal:list[int])->dict[str,object]:
        model=MappingState(**state); start=tuple(model.robot_position); target=(int(goal[0]),int(goal[1])); q=deque([start]); prev={start:None}
        while q:
            cur=q.popleft()
            if cur==target: break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt=(cur[0]+dx,cur[1]+dy)
                if not (0<=nxt[0]<model.width and 0<=nxt[1]<model.height): continue
                if model.grid[nxt[1]][nxt[0]]==1 or nxt in prev: continue
                prev[nxt]=cur; q.append(nxt)
        if target not in prev: return RoutePlan(status='blocked',path=[],reason='no route across known free/unknown cells').to_dict()
        path=[]; cur=target
        while cur is not None: path.append([cur[0],cur[1]]); cur=prev[cur]
        path.reverse(); return RoutePlan(status='ok',path=path,reason='deterministic grid route').to_dict()
