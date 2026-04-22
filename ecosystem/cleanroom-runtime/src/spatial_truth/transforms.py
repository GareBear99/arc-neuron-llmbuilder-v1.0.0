from __future__ import annotations
from math import cos, radians
EARTH_M_PER_DEG_LAT=111_320.0
def geo_to_site_offset_m(origin_lat:float,origin_lon:float,lat:float,lon:float)->tuple[float,float]:
    dy=(lat-origin_lat)*EARTH_M_PER_DEG_LAT; dx=(lon-origin_lon)*EARTH_M_PER_DEG_LAT*cos(radians(origin_lat)); return (dx,dy)
def site_to_geo_offset(origin_lat:float,origin_lon:float,x_m:float,y_m:float)->tuple[float,float]:
    lat=origin_lat+(y_m/EARTH_M_PER_DEG_LAT); lon=origin_lon+(x_m/(EARTH_M_PER_DEG_LAT*cos(radians(origin_lat)) or 1e-9)); return (lat,lon)
