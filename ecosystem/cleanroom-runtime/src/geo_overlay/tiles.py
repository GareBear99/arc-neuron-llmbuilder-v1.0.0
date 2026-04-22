from __future__ import annotations
from typing import Any
from .anchors import tile_key_for_latlon
def summarize_tiles(anchors:list[dict[str,Any]],zoom:int=16)->dict[str,int]:
    out={}
    for a in anchors:
        key=tile_key_for_latlon(float(a['latitude']),float(a['longitude']),zoom=zoom); out[key]=out.get(key,0)+1
    return out
