from __future__ import annotations
import json
from statistics import mean
from arc.core.db import connect
from arc.core.schemas import utcnow, new_id
from arc.geo.geometry import centroid, seeded_point_in_polygon, point_in_polygon, bounds_from_polygon
from arc.geo.estimator import estimate_from_observations, make_observations
from arc.services.audit import append_receipt


def _json_load(value: str):
    return json.loads(value) if isinstance(value, str) else value


def list_structures() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM structures ORDER BY name ASC").fetchall()
        return [
            {
                **dict(r),
                "polygon": _json_load(r["polygon_json"]),
                "center": {"lat": r["center_lat"], "lng": r["center_lng"]},
            }
            for r in rows
        ]


def get_structure(structure_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM structures WHERE structure_id = ?", (structure_id,)).fetchone()
        if not row:
            raise KeyError(structure_id)
        return {
            **dict(row),
            "polygon": _json_load(row["polygon_json"]),
            "center": {"lat": row["center_lat"], "lng": row["center_lng"]},
        }


def create_structure(name: str, address: str, structure_type: str, levels: int, polygon: list[list[float]]) -> dict:
    center = centroid(polygon)
    with connect() as conn:
        existing = conn.execute("SELECT structure_id FROM structures WHERE name = ? AND address = ?", (name, address)).fetchone()
        if existing:
            return get_structure(existing["structure_id"])
        structure_id = new_id("str")
        conn.execute(
            "INSERT INTO structures (structure_id, name, address, structure_type, levels, polygon_json, center_lat, center_lng, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (structure_id, name, address, structure_type, levels, json.dumps(polygon), center["lat"], center["lng"], utcnow()),
        )
        conn.commit()
    append_receipt("structure", structure_id, "analyst", {"name": name, "address": address, "levels": levels})
    return get_structure(structure_id)


def build_sensors_for_structure(structure_id: str) -> list[dict]:
    structure = get_structure(structure_id)
    with connect() as conn:
        existing = conn.execute("SELECT * FROM sensors WHERE structure_id = ? ORDER BY sensor_id ASC", (structure_id,)).fetchall()
        if existing:
            return [dict(r) for r in existing]
        center = structure["center"]
        points = [
            seeded_point_in_polygon(structure["polygon"], 11),
            seeded_point_in_polygon(structure["polygon"], 27),
            seeded_point_in_polygon(structure["polygon"], 53),
            seeded_point_in_polygon(structure["polygon"], 81),
            center,
        ]
        created = []
        for idx, point in enumerate(points, start=1):
            sensor_id = f"{structure_id}-sn{idx}"
            sensor_type = "center-anchor" if idx == 5 else "anchor"
            reliability = 0.98 if idx == 5 else 0.88
            conn.execute(
                "INSERT OR REPLACE INTO sensors (sensor_id, structure_id, label, sensor_type, lat, lng, reliability, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sensor_id, structure_id, f"{structure['name']} Sensor {idx}", sensor_type, point["lat"], point["lng"], reliability, utcnow()),
            )
            created.append(
                {
                    "sensor_id": sensor_id,
                    "structure_id": structure_id,
                    "label": f"{structure['name']} Sensor {idx}",
                    "sensor_type": sensor_type,
                    "lat": point["lat"],
                    "lng": point["lng"],
                    "reliability": reliability,
                }
            )
        conn.commit()
    append_receipt("sensor_batch", structure_id, "analyst", {"count": len(created)})
    return created


def list_sensors(structure_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if structure_id:
            rows = conn.execute("SELECT * FROM sensors WHERE structure_id = ? ORDER BY sensor_id ASC", (structure_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sensors ORDER BY structure_id ASC, sensor_id ASC").fetchall()
        return [dict(r) for r in rows]


def upsert_geofence(name: str, geofence_type: str, structure_id: str | None, polygon: list[list[float]], severity: int = 6) -> dict:
    geofence_id = new_id("geo")
    with connect() as conn:
        conn.execute(
            "INSERT INTO geofences (geofence_id, name, geofence_type, structure_id, polygon_json, severity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (geofence_id, name, geofence_type, structure_id, json.dumps(polygon), severity, utcnow()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM geofences WHERE geofence_id = ?", (geofence_id,)).fetchone()
    append_receipt("geofence", geofence_id, "analyst", {"name": name, "severity": severity})
    return {**dict(row), "polygon": _json_load(row["polygon_json"])}


def list_geofences(structure_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if structure_id:
            rows = conn.execute("SELECT * FROM geofences WHERE structure_id = ? ORDER BY created_at DESC", (structure_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM geofences ORDER BY created_at DESC").fetchall()
        return [{**dict(r), "polygon": _json_load(r["polygon_json"])} for r in rows]


def infer_zone(polygon: list[list[float]], point: dict[str, float]) -> str:
    bounds = bounds_from_polygon(polygon)
    width = bounds["maxLng"] - bounds["minLng"]
    height = bounds["maxLat"] - bounds["minLat"]
    rx = (point["lng"] - bounds["minLng"]) / (width or 1)
    ry = (point["lat"] - bounds["minLat"]) / (height or 1)
    center = abs(rx - 0.5) < 0.18 and abs(ry - 0.5) < 0.18
    if center:
        return "Center-Core"
    if ry < 0.33:
        return "North Zone"
    if ry > 0.66:
        return "South Zone"
    if rx < 0.5:
        return "West Zone"
    return "East Zone"


def _candidate_cloud(structure: dict, point: dict[str, float], confidence: float, count: int = 16) -> list[dict]:
    bounds = bounds_from_polygon(structure["polygon"])
    lat_span = max(0.00001, bounds["maxLat"] - bounds["minLat"])
    lng_span = max(0.00001, bounds["maxLng"] - bounds["minLng"])
    radius_lat = lat_span * (0.02 + (1 - confidence) * 0.12)
    radius_lng = lng_span * (0.02 + (1 - confidence) * 0.12)
    cloud = []
    for idx in range(count):
        angle = (idx / count) * 6.28318530718
        scale = 0.55 + ((idx % 4) / 6)
        candidate = {
            "lat": point["lat"] + radius_lat * scale * __import__("math").sin(angle),
            "lng": point["lng"] + radius_lng * scale * __import__("math").cos(angle),
        }
        if point_in_polygon(candidate, structure["polygon"]):
            cloud.append(candidate)
    return cloud


def estimate_track(subject: str, structure_id: str, observations: list[dict], source: str = "manual", floor: int | None = None) -> dict:
    structure = get_structure(structure_id)
    estimate = estimate_from_observations(observations, structure={"polygon": structure["polygon"]})
    if not estimate:
        raise ValueError("No observations provided")
    point = estimate["point"]
    zone = infer_zone(structure["polygon"], point)
    geofence_hits = []
    with connect() as conn:
        track_id = new_id("trk")
        conn.execute(
            "INSERT INTO track_points (track_id, ts, subject, structure_id, source, lat, lng, confidence, zone, floor, observations_json, estimate_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                track_id,
                utcnow(),
                subject,
                structure_id,
                source,
                point["lat"],
                point["lng"],
                estimate["confidence"],
                zone,
                floor,
                json.dumps(observations),
                json.dumps(estimate),
            ),
        )
        if structure_id:
            fences = conn.execute("SELECT * FROM geofences WHERE structure_id = ? OR structure_id IS NULL", (structure_id,)).fetchall()
        else:
            fences = conn.execute("SELECT * FROM geofences").fetchall()
        for fence in fences:
            polygon = _json_load(fence["polygon_json"])
            if point_in_polygon(point, polygon):
                geofence_hits.append({
                    "geofence_id": fence["geofence_id"],
                    "name": fence["name"],
                    "severity": fence["severity"],
                    "geofence_type": fence["geofence_type"],
                })
        conn.commit()
    result = {
        "track_id": track_id,
        "subject": subject,
        "structure_id": structure_id,
        "point": point,
        "confidence": estimate["confidence"],
        "method": estimate["method"],
        "sensor_count": estimate["sensor_count"],
        "zone": zone,
        "floor": floor,
        "geofence_hits": geofence_hits,
        "candidate_cloud": _candidate_cloud(structure, point, estimate["confidence"]),
    }
    append_receipt("track", track_id, "observer", {"subject": subject, "structure_id": structure_id, "source": source})
    return result


def latest_tracks(limit: int = 100, subject: str | None = None, structure_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if subject and structure_id:
            rows = conn.execute("SELECT * FROM track_points WHERE subject = ? AND structure_id = ? ORDER BY ts DESC LIMIT ?", (subject, structure_id, limit)).fetchall()
        elif subject:
            rows = conn.execute("SELECT * FROM track_points WHERE subject = ? ORDER BY ts DESC LIMIT ?", (subject, limit)).fetchall()
        elif structure_id:
            rows = conn.execute("SELECT * FROM track_points WHERE structure_id = ? ORDER BY ts DESC LIMIT ?", (structure_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM track_points ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [
            {
                **dict(r),
                "observations": _json_load(r["observations_json"]),
                "estimate": _json_load(r["estimate_json"]),
            }
            for r in rows
        ]


def get_heatmap(structure_id: str, grid_size: int = 8) -> dict:
    structure = get_structure(structure_id)
    bounds = bounds_from_polygon(structure["polygon"])
    relevant = latest_tracks(limit=5000, structure_id=structure_id)
    cells = []
    for gy in range(grid_size):
        for gx in range(grid_size):
            min_lat = bounds["minLat"] + (bounds["maxLat"] - bounds["minLat"]) * (gy / grid_size)
            max_lat = bounds["minLat"] + (bounds["maxLat"] - bounds["minLat"]) * ((gy + 1) / grid_size)
            min_lng = bounds["minLng"] + (bounds["maxLng"] - bounds["minLng"]) * (gx / grid_size)
            max_lng = bounds["minLng"] + (bounds["maxLng"] - bounds["minLng"]) * ((gx + 1) / grid_size)
            count = 0
            confidence_values = []
            center = {"lat": (min_lat + max_lat) / 2, "lng": (min_lng + max_lng) / 2}
            if not point_in_polygon(center, structure["polygon"]):
                continue
            for track in relevant:
                if min_lat <= track["lat"] <= max_lat and min_lng <= track["lng"] <= max_lng:
                    count += 1
                    confidence_values.append(track["confidence"])
            cells.append({
                "gx": gx,
                "gy": gy,
                "count": count,
                "mean_confidence": round(mean(confidence_values), 3) if confidence_values else 0.0,
                "center": center,
            })
    return {"structure_id": structure_id, "grid_size": grid_size, "cells": cells}


def upsert_blueprint_overlay(structure_id: str, name: str, image_url: str, opacity: float, scale: float, offset_x: float, offset_y: float, rotation_deg: float, floor: int | None = None) -> dict:
    get_structure(structure_id)
    now = utcnow()
    with connect() as conn:
        existing = conn.execute(
            "SELECT overlay_id, created_at FROM blueprint_overlays WHERE structure_id = ? AND name = ? AND ifnull(floor, -1) = ifnull(?, -1)",
            (structure_id, name, floor),
        ).fetchone()
        if existing:
            overlay_id = existing["overlay_id"]
            created_at = existing["created_at"]
            conn.execute(
                "UPDATE blueprint_overlays SET image_url = ?, opacity = ?, scale = ?, offset_x = ?, offset_y = ?, rotation_deg = ?, updated_at = ? WHERE overlay_id = ?",
                (image_url, opacity, scale, offset_x, offset_y, rotation_deg, now, overlay_id),
            )
        else:
            overlay_id = new_id("ovr")
            created_at = now
            conn.execute(
                "INSERT INTO blueprint_overlays (overlay_id, structure_id, name, image_url, opacity, scale, offset_x, offset_y, rotation_deg, floor, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (overlay_id, structure_id, name, image_url, opacity, scale, offset_x, offset_y, rotation_deg, floor, created_at, now),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM blueprint_overlays WHERE overlay_id = ?", (overlay_id,)).fetchone()
    append_receipt("overlay", overlay_id, "analyst", {"structure_id": structure_id, "name": name})
    return dict(row)


def list_blueprint_overlays(structure_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if structure_id:
            rows = conn.execute("SELECT * FROM blueprint_overlays WHERE structure_id = ? ORDER BY updated_at ASC", (structure_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM blueprint_overlays ORDER BY updated_at ASC").fetchall()
        return [dict(r) for r in rows]


def create_calibration_profile(structure_id: str, name: str, path_loss: float, noise_db: float, smoothing: float, notes: str = "") -> dict:
    get_structure(structure_id)
    profile = {"path_loss": path_loss, "noise_db": noise_db, "smoothing": smoothing}
    now = utcnow()
    with connect() as conn:
        existing = conn.execute("SELECT profile_id, created_at FROM calibration_profiles WHERE structure_id = ? AND name = ?", (structure_id, name)).fetchone()
        if existing:
            profile_id = existing["profile_id"]
            created_at = existing["created_at"]
            conn.execute(
                "UPDATE calibration_profiles SET profile_json = ?, notes = ?, updated_at = ? WHERE profile_id = ?",
                (json.dumps(profile, sort_keys=True), notes, now, profile_id),
            )
        else:
            profile_id = new_id("cal")
            created_at = now
            conn.execute(
                "INSERT INTO calibration_profiles (profile_id, structure_id, name, profile_json, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (profile_id, structure_id, name, json.dumps(profile, sort_keys=True), notes, created_at, now),
            )
        conn.commit()
    append_receipt("calibration", profile_id, "analyst", {"structure_id": structure_id, "name": name, **profile})
    return list_calibration_profiles(structure_id)[-1]


def list_calibration_profiles(structure_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if structure_id:
            rows = conn.execute("SELECT * FROM calibration_profiles WHERE structure_id = ? ORDER BY updated_at ASC", (structure_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM calibration_profiles ORDER BY updated_at ASC").fetchall()
        return [{**dict(r), "profile": _json_load(r["profile_json"])} for r in rows]


def import_track_points(subject: str, structure_id: str, source: str, track_points: list[dict]) -> dict:
    structure = get_structure(structure_id)
    imported = []
    with connect() as conn:
        for point in track_points:
            zone = point.get("zone") or infer_zone(structure["polygon"], {"lat": point["lat"], "lng": point["lng"]})
            track_id = new_id("trk")
            estimate = {"method": "import", "source": source, "payload": point.get("payload", {})}
            conn.execute(
                "INSERT INTO track_points (track_id, ts, subject, structure_id, source, lat, lng, confidence, zone, floor, observations_json, estimate_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (track_id, point.get("ts") or utcnow(), subject, structure_id, source, point["lat"], point["lng"], point.get("confidence", 0.7), zone, point.get("floor"), json.dumps([]), json.dumps(estimate)),
            )
            imported.append({"track_id": track_id, "zone": zone, "lat": point["lat"], "lng": point["lng"]})
        conn.commit()
    append_receipt("track_import", subject, "observer", {"structure_id": structure_id, "source": source, "count": len(imported)})
    return {"subject": subject, "structure_id": structure_id, "imported_count": len(imported), "tracks": imported}


def create_incident(title: str, severity: str, status: str, subject: str | None = None, structure_id: str | None = None, details: dict | None = None) -> dict:
    incident_id = new_id("inc")
    payload = details or {}
    ts = utcnow()
    with connect() as conn:
        conn.execute(
            "INSERT INTO incidents (incident_id, ts, title, severity, status, subject, structure_id, detail_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (incident_id, ts, title, severity, status, subject, structure_id, json.dumps(payload, sort_keys=True)),
        )
        conn.commit()
    append_receipt("incident", incident_id, "analyst", {"title": title, "severity": severity, "status": status, "subject": subject})
    return list_incidents()[0]


def list_incidents(limit: int = 100) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM incidents ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "details": _json_load(r["detail_json"])} for r in rows]


def export_evidence_pack(case_id: str | None = None, subject: str | None = None) -> dict:
    with connect() as conn:
        case = None
        events = []
        tracks = []
        linked_subjects = set()
        if case_id:
            case = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            event_rows = conn.execute(
                "SELECT e.* FROM case_events ce JOIN events e ON e.id = ce.event_id WHERE ce.case_id = ? ORDER BY e.ts DESC",
                (case_id,),
            ).fetchall()
            events = [{**dict(r), "payload": _json_load(r["payload_json"])} for r in event_rows]
            for e in events:
                linked_subjects.add(e["subject"])
                if e.get("object"):
                    linked_subjects.add(e["object"])
        if subject:
            subject_entity = None
            row = conn.execute("SELECT entity_id FROM entities WHERE label = ? OR lower(label) = lower(?) LIMIT 1", (subject, subject)).fetchone()
            if row:
                subject_entity = row["entity_id"]
                linked_subjects.add(subject_entity)
            linked_subjects.add(subject)
            track_rows = conn.execute("SELECT * FROM track_points WHERE subject = ? ORDER BY ts DESC LIMIT 250", (subject,)).fetchall()
            tracks = [{**dict(r), "estimate": _json_load(r["estimate_json"]), "observations": _json_load(r["observations_json"])} for r in track_rows]
            if not events:
                if subject_entity:
                    event_rows = conn.execute("SELECT * FROM events WHERE subject = ? OR object = ? OR subject = ? OR object = ? ORDER BY ts DESC LIMIT 250", (subject, subject, subject_entity, subject_entity)).fetchall()
                else:
                    event_rows = conn.execute("SELECT * FROM events WHERE subject = ? OR object = ? ORDER BY ts DESC LIMIT 250", (subject, subject)).fetchall()
                events = [{**dict(r), "payload": _json_load(r["payload_json"])} for r in event_rows]
                for e in events:
                    linked_subjects.add(e["subject"])
                    if e.get("object"):
                        linked_subjects.add(e["object"])
        entities = []
        if linked_subjects:
            placeholders = ",".join(["?"] * len(linked_subjects))
            rows = conn.execute(f"SELECT * FROM entities WHERE entity_id IN ({placeholders}) ORDER BY risk_score DESC", tuple(linked_subjects)).fetchall()
            for row in rows:
                item = dict(row)
                item["aliases"] = _json_load(item.pop("aliases_json"))
                entities.append(item)
        edges = []
        if linked_subjects:
            placeholders = ",".join(["?"] * len(linked_subjects))
            rows = conn.execute(f"SELECT * FROM edges WHERE src_entity IN ({placeholders}) OR dst_entity IN ({placeholders}) ORDER BY weight DESC, last_seen DESC LIMIT 250", tuple(linked_subjects) + tuple(linked_subjects)).fetchall()
            edges = [dict(r) for r in rows]
        notes = []
        if case_id:
            rows = conn.execute("SELECT * FROM analyst_notes WHERE subject_type = 'case' AND subject_id = ? ORDER BY created_at DESC LIMIT 100", (case_id,)).fetchall()
            notes.extend([{**dict(r), "tags": _json_load(r["tags_json"])} for r in rows])
        if subject:
            rows = conn.execute("SELECT * FROM analyst_notes WHERE subject_type = 'subject' AND subject_id = ? ORDER BY created_at DESC LIMIT 100", (subject,)).fetchall()
            notes.extend([{**dict(r), "tags": _json_load(r["tags_json"])} for r in rows])
        receipts = []
        for row in conn.execute("SELECT * FROM receipt_chain ORDER BY ts DESC LIMIT 250").fetchall():
            receipts.append({**dict(row), "payload": _json_load(row["payload_json"])})
    return {
        "exported_at": utcnow(),
        "case": dict(case) if case else None,
        "subject": subject,
        "events": events,
        "tracks": tracks,
        "entities": entities,
        "edges": edges,
        "notes": notes,
        "summary": {
            "event_count": len(events),
            "track_count": len(tracks),
            "entity_count": len(entities),
            "edge_count": len(edges),
            "note_count": len(notes),
        },
        "receipt_chain_tail": receipts[0]["hash"] if receipts else "GENESIS",
        "receipt_count": len(receipts),
        "receipts": receipts[:50],
    }


def generate_demo_track(subject: str, structure_id: str) -> dict:
    sensors = build_sensors_for_structure(structure_id)
    structure = get_structure(structure_id)
    truth = seeded_point_in_polygon(structure["polygon"], 144.0)
    observations = make_observations(truth, sensors)
    result = estimate_track(subject=subject, structure_id=structure_id, observations=observations, source="demo-rf")
    result["truth"] = truth
    return result
