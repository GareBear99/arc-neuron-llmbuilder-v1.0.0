from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse
from arc.core.auth import require_role
from arc.core.config import APP_NAME, APP_VERSION, DEFAULT_LIMIT, MAX_GRID_SIZE, MAX_LIMIT, RECEIPT_VERIFY_MAX
from arc.core.db import connect
from arc.core.schemas import (
    EventIn, WatchlistIn, CaseIn, ProposalIn, StructureIn, GeofenceIn, TrackEstimateIn,
    BlueprintOverlayIn, CalibrationProfileIn, TrackImportIn, IncidentIn, LoginIn, ConnectorIn, NoteIn,
)
from arc.services.audit import log, list_receipts, verify_receipt_chain
from arc.services.authn import ensure_bootstrap_admin, login, resolve_session
from arc.services.connectors import create_connector, list_connectors, poll_connector
from arc.services.ingest import create_event, list_events
from arc.services.graph import snapshot
from arc.services.watchlists import create_watchlist, list_watchlists
from arc.services.cases import create_case, list_cases, get_case, attach_event
from arc.services.proposals import create_proposal, approve_proposal, list_proposals
from arc.services.geospatial import (
    create_structure, list_structures, get_structure, build_sensors_for_structure, list_sensors,
    upsert_geofence, list_geofences, estimate_track, latest_tracks, generate_demo_track,
    upsert_blueprint_overlay, list_blueprint_overlays, create_calibration_profile,
    list_calibration_profiles, get_heatmap, import_track_points, create_incident,
    list_incidents, export_evidence_pack,
)
from arc.services.notebook import create_note, list_notes
from arc.core.simulator import simulate

router = APIRouter()
ROOT_UI = Path(__file__).resolve().parents[1] / "ui" / "dashboard.html"


def role_observer(x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    return require_role("observer", x_arc_role, x_arc_token, authorization)


def role_analyst(x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    return require_role("analyst", x_arc_role, x_arc_token, authorization)


def role_operator(x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    return require_role("operator", x_arc_role, x_arc_token, authorization)


def role_approver(x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    return require_role("approver", x_arc_role, x_arc_token, authorization)


def role_admin(x_arc_role: str = Header(default="observer"), x_arc_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    return require_role("admin", x_arc_role, x_arc_token, authorization)


def _bounded(limit: int) -> int:
    return max(1, min(MAX_LIMIT, limit))


@router.get("/")
def home():
    return FileResponse(ROOT_UI)


@router.get("/health")
def health():
    return {"ok": True, "service": APP_NAME, "version": APP_VERSION}


@router.get("/api/manifest")
def manifest():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "capabilities": [
            "event_ingest", "entity_resolution", "graph_snapshot", "geo_estimation", "heatmap",
            "blueprint_overlay", "calibration_profiles", "track_import", "evidence_export",
            "tamper_evident_receipts", "signed_receipts", "auth_sessions", "connector_bus", "analyst_notebook",
        ],
        "ui": ["dashboard", "signals", "graph", "timeline", "cases", "geo"],
    }


@router.post("/api/auth/bootstrap")
def auth_bootstrap():
    return ensure_bootstrap_admin()


@router.post("/api/auth/login")
def auth_login(payload: LoginIn):
    try:
        return login(payload)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/api/auth/session")
def auth_session(authorization: str | None = Header(default=None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    session = resolve_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"session": session}


@router.post("/api/events")
def post_event(event: EventIn, role: str = Depends(role_observer)):
    out = create_event(event)
    log(role, "create_event", out.id, out.model_dump())
    return out


@router.get("/api/events")
def get_events(limit: int = Query(default=50, ge=1, le=MAX_LIMIT), q: str | None = None):
    return {"events": list_events(limit=_bounded(limit), q=q)}


@router.get("/api/entities")
def get_entities(limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM entities ORDER BY risk_score DESC, last_seen DESC LIMIT ?", (_bounded(limit),)).fetchall()
        entities = []
        for r in rows:
            item = dict(r)
            item["aliases"] = json.loads(item.pop("aliases_json"))
            entities.append(item)
        return {"entities": entities}


@router.get("/api/entities/{entity_id}")
def get_entity(entity_id: str):
    with connect() as conn:
        entity = conn.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,)).fetchone()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        events = conn.execute("SELECT * FROM events WHERE subject = ? OR object = ? ORDER BY ts DESC LIMIT 100", (entity_id, entity_id)).fetchall()
        entity_dict = dict(entity)
        entity_dict["aliases"] = json.loads(entity_dict.pop("aliases_json"))
        notes = list_notes(subject_type="entity", subject_id=entity_id, limit=50)
        return {"entity": entity_dict, "events": [{**dict(r), "payload": json.loads(r["payload_json"])} for r in events], "notes": notes}


@router.get("/api/graph")
def get_graph(limit: int = Query(default=200, ge=1, le=MAX_LIMIT)):
    return snapshot(limit=_bounded(limit))


@router.get("/api/timeline")
def timeline(limit: int = Query(default=150, ge=1, le=MAX_LIMIT)):
    events = list_events(limit=_bounded(limit))
    return {"timeline": [{"id": e["id"], "ts": e["ts"], "title": f'{e["event_type"]}: {e["subject"]} -> {e.get("object") or "-"}', "severity": e["severity"], "source": e["source"], "location": e.get("location"), "payload": e["payload"]} for e in events]}


@router.post("/api/watchlists")
def post_watchlist(item: WatchlistIn, role: str = Depends(role_analyst)):
    out = create_watchlist(item)
    log(role, "create_watchlist", out["watchlist_id"], out)
    return out


@router.get("/api/watchlists")
def get_watchlists():
    return {"watchlists": list_watchlists()}


@router.post("/api/cases")
def post_case(case: CaseIn, role: str = Depends(role_analyst)):
    out = create_case(case)
    log(role, "create_case", out["case_id"], out)
    return out


@router.get("/api/cases")
def get_cases():
    return {"cases": list_cases()}


@router.get("/api/cases/{case_id}")
def read_case(case_id: str):
    try:
        body = get_case(case_id)
        body["notes"] = list_notes(subject_type="case", subject_id=case_id, limit=100)
        return body
    except KeyError:
        raise HTTPException(status_code=404, detail="Case not found")


@router.post("/api/cases/{case_id}/attach/{event_id}")
def post_attach(case_id: str, event_id: str, role: str = Depends(role_analyst)):
    try:
        out = attach_event(case_id, event_id)
    except KeyError as exc:
        detail = "Case not found" if str(exc) == repr(case_id) else "Event not found"
        raise HTTPException(status_code=404, detail=detail)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    log(role, "attach_case_event", case_id, {"event_id": event_id})
    return out


@router.get("/api/evidence")
def get_evidence(case_id: str | None = None, subject: str | None = None):
    if not case_id and not subject:
        raise HTTPException(status_code=400, detail="case_id or subject is required")
    return export_evidence_pack(case_id=case_id, subject=subject)


@router.post("/api/proposals")
def post_proposal(prop: ProposalIn, role: str = Depends(role_operator)):
    with connect() as conn:
        row = conn.execute("SELECT risk_score FROM entities WHERE entity_id = ?", (prop.target_id,)).fetchone()
        risk_score = float(row["risk_score"]) if row else 20.0
    out = create_proposal(prop, created_by_role=role, risk_score=risk_score)
    log(role, "create_proposal", out.proposal_id, out.model_dump())
    return out


@router.post("/api/proposals/{proposal_id}/approve")
def post_approve(proposal_id: str, role: str = Depends(role_approver)):
    try:
        out = approve_proposal(proposal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    log(role, "approve_proposal", proposal_id, out.model_dump())
    return out


@router.get("/api/proposals")
def get_proposals():
    return {"proposals": list_proposals()}


@router.get("/api/simulate/{target_id}")
def get_simulate(target_id: str, action: str = "observe", depth: int = Query(default=2, ge=1, le=5)):
    with connect() as conn:
        row = conn.execute("SELECT risk_score FROM entities WHERE entity_id = ?", (target_id,)).fetchone()
        risk_score = float(row["risk_score"]) if row else 20.0
    return simulate(action=action, target_id=target_id, risk_score=risk_score, depth=depth)


@router.get("/api/audit")
def get_audit(limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY ts DESC LIMIT ?", (_bounded(limit),)).fetchall()
        return {"audit": [{**dict(r), "detail": json.loads(r["detail_json"])} for r in rows]}


@router.get("/api/receipts")
def get_receipts(limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    return {"receipts": list_receipts(limit=_bounded(limit))}


@router.get("/api/receipts/verify")
def verify_receipts(limit: int | None = Query(default=None, ge=1, le=RECEIPT_VERIFY_MAX)):
    return verify_receipt_chain(limit=limit)


@router.post("/api/connectors")
def post_connector(item: ConnectorIn, role: str = Depends(role_admin)):
    out = create_connector(item)
    log(role, "upsert_connector", out["connector_id"], out)
    return out


@router.get("/api/connectors")
def get_connectors():
    return {"connectors": list_connectors()}


@router.post("/api/connectors/{connector_id}/poll")
def post_poll_connector(connector_id: str, role: str = Depends(role_admin)):
    try:
        out = poll_connector(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Connector not found")
    log(role, "poll_connector", connector_id, out)
    return out


@router.post("/api/notes")
def post_note(item: NoteIn, role: str = Depends(role_analyst)):
    out = create_note(item, actor_role=role)
    log(role, "create_note", out["note_id"], out)
    return out


@router.get("/api/notes")
def get_notes(subject_type: str | None = None, subject_id: str | None = None, limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    return {"notes": list_notes(subject_type=subject_type, subject_id=subject_id, limit=_bounded(limit))}


@router.post("/api/geo/structures")
def post_structure(item: StructureIn, role: str = Depends(role_analyst)):
    out = create_structure(item.name, item.address, item.structure_type, item.levels, item.polygon)
    log(role, "create_structure", out["structure_id"], out)
    return out


@router.get("/api/geo/structures")
def get_structures():
    return {"structures": list_structures()}


@router.get("/api/geo/structures/{structure_id}")
def read_structure(structure_id: str):
    try:
        return get_structure(structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Structure not found")


@router.post("/api/geo/structures/{structure_id}/sensors")
def post_structure_sensors(structure_id: str, role: str = Depends(role_analyst)):
    try:
        out = build_sensors_for_structure(structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Structure not found")
    log(role, "build_sensors", structure_id, {"count": len(out)})
    return {"sensors": out}


@router.get("/api/geo/sensors")
def get_sensors(structure_id: str | None = None):
    return {"sensors": list_sensors(structure_id=structure_id)}


@router.post("/api/geo/geofences")
def post_geofence(item: GeofenceIn, role: str = Depends(role_analyst)):
    out = upsert_geofence(item.name, item.geofence_type, item.structure_id, item.polygon, item.severity)
    log(role, "create_geofence", out["geofence_id"], out)
    return out


@router.get("/api/geo/geofences")
def get_geofences(structure_id: str | None = None):
    return {"geofences": list_geofences(structure_id=structure_id)}


@router.post("/api/geo/estimate")
def post_geo_estimate(item: TrackEstimateIn, role: str = Depends(role_observer)):
    sensors = {row["sensor_id"]: row for row in list_sensors(item.structure_id)}
    observations = []
    for obs in item.observations:
        sensor = sensors.get(obs.sensor_id)
        if not sensor:
            raise HTTPException(status_code=400, detail=f"Unknown sensor_id: {obs.sensor_id}")
        observations.append({"sensor_id": sensor["sensor_id"], "sensor_lat": sensor["lat"], "sensor_lng": sensor["lng"], "rssi": obs.rssi, "reliability": obs.reliability if obs.reliability is not None else sensor.get("reliability", 1.0)})
    try:
        out = estimate_track(item.subject, item.structure_id, observations, source=item.source, floor=item.floor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Structure not found")
    log(role, "estimate_track", out["track_id"], out)
    return out


@router.post("/api/geo/demo-track/{structure_id}")
def post_demo_track(structure_id: str, subject: str = "Demo Device", role: str = Depends(role_observer)):
    try:
        out = generate_demo_track(subject, structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Structure not found")
    log(role, "generate_demo_track", out["track_id"], out)
    return out


@router.get("/api/geo/tracks")
def get_tracks(limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), subject: str | None = None, structure_id: str | None = None):
    return {"tracks": latest_tracks(limit=_bounded(limit), subject=subject, structure_id=structure_id)}


@router.get("/api/geo/heatmap/{structure_id}")
def geo_heatmap(structure_id: str, grid_size: int = Query(default=8, ge=2, le=MAX_GRID_SIZE)):
    return get_heatmap(structure_id=structure_id, grid_size=grid_size)


@router.post("/api/geo/blueprints")
def post_blueprint(item: BlueprintOverlayIn, role: str = Depends(role_analyst)):
    out = upsert_blueprint_overlay(**item.model_dump())
    log(role, "upsert_blueprint_overlay", out["overlay_id"], out)
    return out


@router.get("/api/geo/blueprints")
def get_blueprints(structure_id: str | None = None):
    return {"blueprints": list_blueprint_overlays(structure_id=structure_id)}


@router.post("/api/geo/calibrations")
def post_calibration(item: CalibrationProfileIn, role: str = Depends(role_analyst)):
    out = create_calibration_profile(**item.model_dump())
    log(role, "upsert_calibration_profile", out["profile_id"], out)
    return out


@router.get("/api/geo/calibrations")
def get_calibrations(structure_id: str | None = None):
    return {"calibrations": list_calibration_profiles(structure_id=structure_id)}


@router.post("/api/geo/import-tracks")
def post_import_tracks(item: TrackImportIn, role: str = Depends(role_observer)):
    out = import_track_points(item.subject, item.structure_id, item.source, [tp.model_dump() for tp in item.track_points])
    log(role, "import_tracks", item.subject, {"count": out["imported_count"], "structure_id": item.structure_id})
    return out


@router.post("/api/incidents")
def post_incident(item: IncidentIn, role: str = Depends(role_analyst)):
    out = create_incident(item.title, item.severity, item.status, item.subject, item.structure_id, item.details)
    log(role, "create_incident", out["incident_id"], out)
    return out


@router.get("/api/incidents")
def get_incidents(limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    return {"incidents": list_incidents(limit=_bounded(limit))}
