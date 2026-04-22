from __future__ import annotations
from math import floor
def canonicalize_address(raw:str)->str: return ' '.join(raw.strip().lower().replace(',', ' ').split())
def tile_key_for_latlon(lat:float,lon:float,zoom:int=16)->str:
    scale=max(1,2**min(max(0,zoom),20)); x=floor((lon+180.0)/360.0*scale); y=floor((lat+90.0)/180.0*scale); return f'z{zoom}:{x}:{y}'
