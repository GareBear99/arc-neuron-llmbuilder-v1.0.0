"""Geo overlay helpers inspired by local address tiling concepts."""
from .anchors import canonicalize_address, tile_key_for_latlon
from .gateway import GeoOverlayGateway
__all__=['canonicalize_address','tile_key_for_latlon','GeoOverlayGateway']
