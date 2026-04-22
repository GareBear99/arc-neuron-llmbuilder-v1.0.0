from __future__ import annotations
from typing import Any
from .anchors import canonicalize_address, tile_key_for_latlon
from .tiles import summarize_tiles
class GeoOverlayGateway:
    def describe(self)->dict[str,Any]: return {'status':'ok','required':False,'capabilities':['address_anchor_vault','nearest_anchor','tile_summary'],'doctrine':'local semantic geo overlay beneath the spatial truth layer'}
    def anchor_template(self)->dict[str,Any]: return {'status':'ok','anchor_template':{'anchor_id':'home-base','label':'home base','address':'123 Example St','latitude':0.0,'longitude':0.0}}
    def register_anchor(self,anchors:list[dict[str,Any]],anchor:dict[str,Any])->dict[str,Any]:
        norm=dict(anchor); norm['address_canonical']=canonicalize_address(anchor.get('address','')); norm['tile_key']=tile_key_for_latlon(float(anchor['latitude']),float(anchor['longitude']),zoom=int(anchor.get('zoom',16))); items=[a for a in anchors if a.get('anchor_id')!=norm['anchor_id']]+[norm]; return {'status':'ok','anchors':items,'tile_summary':summarize_tiles(items,zoom=int(anchor.get('zoom',16)))}
    def nearest_anchor(self,anchors:list[dict[str,Any]],lat:float,lon:float)->dict[str,Any]:
        if not anchors: return {'status':'not_found','reason':'no anchors registered'}
        best=min(anchors,key=lambda a: abs(float(a['latitude'])-lat)+abs(float(a['longitude'])-lon)); return {'status':'ok','nearest_anchor':best}
    def tile_summary(self,anchors:list[dict[str,Any]],zoom:int=16)->dict[str,Any]: return {'status':'ok','tile_summary':summarize_tiles(anchors,zoom=zoom)}
