from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(slots=True)
class SpatialAnchor:
    anchor_id:str
    label:str
    latitude:float
    longitude:float
    floor:str='site'
    confidence:float=1.0
    metadata:dict[str,Any]=field(default_factory=dict)
    def to_dict(self)->dict[str,Any]: return asdict(self)

@dataclass(slots=True)
class SpatialObservation:
    source:str
    kind:str
    label:str
    confidence:float
    x_m:float
    y_m:float
    z_m:float=0.0
    metadata:dict[str,Any]=field(default_factory=dict)
    def to_dict(self)->dict[str,Any]: return asdict(self)

@dataclass(slots=True)
class SpatialWorldState:
    anchors:list[dict[str,Any]]=field(default_factory=list)
    observations:list[dict[str,Any]]=field(default_factory=list)
    confidence_world:dict[str,Any]=field(default_factory=lambda:{'average_confidence':1.0,'observation_count':0})
    def to_dict(self)->dict[str,Any]: return asdict(self)
