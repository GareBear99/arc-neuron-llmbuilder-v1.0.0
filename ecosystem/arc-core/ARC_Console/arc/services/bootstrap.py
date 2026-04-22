from __future__ import annotations
from arc.core.db import init_db, connect
from arc.core.schemas import EventIn
from arc.services.authn import ensure_bootstrap_admin
from arc.services.connectors import ensure_demo_connector, poll_connector
from arc.services.ingest import create_event
from arc.services.geospatial import (
    create_structure,
    build_sensors_for_structure,
    upsert_geofence,
    list_structures,
    generate_demo_track,
    upsert_blueprint_overlay,
    create_calibration_profile,
    create_incident,
)


def seed_demo() -> None:
    init_db()
    ensure_bootstrap_admin()
    with connect() as conn:
        c = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
    if c == 0:
        create_event(EventIn(event_type="login", source="seed", subject="Gary", object="Console", location="Williams Lake", confidence=0.92, severity=3, payload={"ip": "10.0.0.10"}))
        create_event(EventIn(event_type="transfer", source="seed", subject="Drone-7", object="Cache-A", location="Sector North", confidence=0.74, severity=6, payload={"units": 4}))
        create_event(EventIn(event_type="meeting", source="seed", subject="Analyst K", object="Node-4", location="Vancouver", confidence=0.81, severity=4, payload={"duration_min": 35}))
    if not list_structures():
        structures = [
            {"name": "Pine House", "address": "100 Pine Ave", "structure_type": "house", "levels": 1, "polygon": [[52.13188, -122.14235], [52.13188, -122.14203], [52.13168, -122.14203], [52.13168, -122.14235]]},
            {"name": "Cedar Duplex", "address": "118 Cedar St", "structure_type": "duplex", "levels": 2, "polygon": [[52.13156, -122.14174], [52.13156, -122.14137], [52.13132, -122.14137], [52.13132, -122.14174]]},
            {"name": "Lakeview Home", "address": "240 Lakeview Dr", "structure_type": "house", "levels": 2, "polygon": [[52.13207, -122.14148], [52.13207, -122.14112], [52.13179, -122.14112], [52.13179, -122.14148]]},
        ]
        created = []
        for s in structures:
            created.append(create_structure(**s))
        for s in created:
            build_sensors_for_structure(s["structure_id"])
            upsert_geofence(name=f"{s['name']} Perimeter", geofence_type="structure", structure_id=s["structure_id"], polygon=s["polygon"], severity=5)
            upsert_blueprint_overlay(s["structure_id"], f"{s['name']} Floorplan", f"https://example.local/{s['structure_id']}/floorplan.png", 0.45, 1.0, 0.0, 0.0, 0.0, 1)
            create_calibration_profile(s["structure_id"], f"{s['name']} Default", 2.2, 3.5, 0.65, "Seeded indoor profile")
        demo = generate_demo_track("Demo Device", created[0]["structure_id"])
        create_incident("Initial breach watch", "medium", "open", "Demo Device", created[0]["structure_id"], {"track_id": demo["track_id"], "zone": demo["zone"]})
    connector = ensure_demo_connector()
    poll_connector(connector["connector_id"])
