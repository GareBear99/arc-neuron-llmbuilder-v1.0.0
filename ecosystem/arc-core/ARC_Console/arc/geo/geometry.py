from __future__ import annotations
from math import atan2, cos, radians, sin, sqrt


def centroid(polygon: list[list[float]]) -> dict[str, float]:
    lat = sum(p[0] for p in polygon) / len(polygon)
    lng = sum(p[1] for p in polygon) / len(polygon)
    return {"lat": lat, "lng": lng}


def bounds_from_polygon(poly: list[list[float]]) -> dict[str, float]:
    lats = [p[0] for p in poly]
    lngs = [p[1] for p in poly]
    return {
        "minLat": min(lats),
        "maxLat": max(lats),
        "minLng": min(lngs),
        "maxLng": max(lngs),
    }


def point_in_polygon(point: dict[str, float], polygon: list[list[float]]) -> bool:
    x = point["lng"]
    y = point["lat"]
    inside = False
    for i in range(len(polygon)):
        j = (i - 1) % len(polygon)
        xi, yi = polygon[i][1], polygon[i][0]
        xj, yj = polygon[j][1], polygon[j][0]
        denom = (yj - yi) if (yj - yi) != 0 else 1e-12
        intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / denom + xi)
        if intersect:
            inside = not inside
    return inside


def clamp_point_to_bounds(point: dict[str, float], bounds: dict[str, float]) -> dict[str, float]:
    return {
        "lat": min(bounds["maxLat"], max(bounds["minLat"], point["lat"])),
        "lng": min(bounds["maxLng"], max(bounds["minLng"], point["lng"])),
    }


def seeded(seed: float) -> float:
    x = sin(seed) * 10000
    return x - int(x)


def seeded_point_in_polygon(polygon: list[list[float]], seed_value: float = 1.0) -> dict[str, float]:
    bounds = bounds_from_polygon(polygon)
    for idx in range(300):
        r1 = seeded(seed_value + idx * 2.17)
        r2 = seeded(seed_value + idx * 3.41 + 9.2)
        candidate = {
            "lat": bounds["minLat"] + (bounds["maxLat"] - bounds["minLat"]) * r1,
            "lng": bounds["minLng"] + (bounds["maxLng"] - bounds["minLng"]) * r2,
        }
        if point_in_polygon(candidate, polygon):
            return candidate
    return centroid(polygon)


def distance_meters(a: dict[str, float], b: dict[str, float]) -> float:
    earth_radius = 6_371_000
    d_lat = radians(b["lat"] - a["lat"])
    d_lng = radians(b["lng"] - a["lng"])
    lat1 = radians(a["lat"])
    lat2 = radians(b["lat"])
    hav = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lng / 2) ** 2
    return 2 * earth_radius * atan2(sqrt(hav), sqrt(1 - hav))
