from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
@dataclass(slots=True)
class GridUpdate: x:int; y:int; value:int
@dataclass(slots=True)
class RoutePlan:
    status:str; path:list[list[int]]=field(default_factory=list); reason:str=''
    def to_dict(self)->dict[str,Any]: return asdict(self)
@dataclass(slots=True)
class MappingState:
    width:int=8; height:int=8; grid:list[list[int]]=field(default_factory=lambda:[[-1 for _ in range(8)] for _ in range(8)]); robot_position:list[int]=field(default_factory=lambda:[0,0])
    def to_dict(self)->dict[str,Any]: return asdict(self)
