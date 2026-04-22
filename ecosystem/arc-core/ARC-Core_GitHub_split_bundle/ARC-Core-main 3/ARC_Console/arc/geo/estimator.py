from __future__ import annotations
from arc.geo.geometry import (
    bounds_from_polygon,
    clamp_point_to_bounds,
    distance_meters,
    point_in_polygon,
)


def rssi_from_distance_meters(meters: float, noise_db: float = 2.5) -> float:
    d = max(1.0, meters)
    path_loss = 32 + 20 * __import__("math").log10(d)
    tx = -30.0
    return tx - path_loss + noise_db * 0.0


def estimate_from_observations(observations: list[dict], structure: dict | None = None) -> dict | None:
    if not observations:
        return None
    sum_w = 0.0
    lat = 0.0
    lng = 0.0
    for obs in observations:
        reliability = float(obs.get("reliability", 1.0))
        rssi = float(obs["rssi"])
        weight = max(0.0001, pow(10, (rssi + 100.0) / 12.0)) * max(0.2, reliability)
        sum_w += weight
        lat += float(obs["sensor_lat"]) * weight
        lng += float(obs["sensor_lng"]) * weight
    point = {"lat": lat / sum_w, "lng": lng / sum_w}
    if structure:
        polygon = structure["polygon"] if isinstance(structure["polygon"], list) else structure.get("polygon")
        if polygon and not point_in_polygon(point, polygon):
            point = clamp_point_to_bounds(point, bounds_from_polygon(polygon))
    sorted_obs = sorted(observations, key=lambda o: o["rssi"], reverse=True)
    spread = abs(sorted_obs[0]["rssi"] - sorted_obs[1]["rssi"]) if len(sorted_obs) >= 2 else 0.0
    avg_rel = sum(float(o.get("reliability", 1.0)) for o in observations) / len(observations)
    confidence = max(0.15, min(0.99, 0.32 + spread / 22.0 + avg_rel * 0.25))
    return {
        "point": point,
        "confidence": round(confidence, 4),
        "method": "weighted-rssi-centroid",
        "sensor_count": len(observations),
    }


def make_observations(truth: dict[str, float], sensors: list[dict], noise_db: float = 2.5) -> list[dict]:
    out = []
    for sensor in sensors:
        out.append(
            {
                "sensor_id": sensor["sensor_id"],
                "sensor_lat": sensor["lat"],
                "sensor_lng": sensor["lng"],
                "rssi": round(rssi_from_distance_meters(distance_meters(truth, sensor), noise_db=noise_db), 2),
                "reliability": sensor.get("reliability", 1.0),
            }
        )
    return out
