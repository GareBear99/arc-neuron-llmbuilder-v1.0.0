# ARC-Core Code Surface Audit

This inventory was generated after reconstructing the working split-bundle package and reading the Python code surface file-by-file.

- Python files: **39**
- Python lines across those files: **2611**
- Top-level functions: **160**
- Top-level classes: **18**

## `run_arc.py`

- Lines: 1
- Classes: None
- Top-level functions: None

## `seed_demo.py`

- Lines: 5
- Classes: None
- Top-level functions: None

## `arc/__init__.py`

- Lines: 0
- Classes: None
- Top-level functions: None

## `arc/api/__init__.py`

- Lines: 0
- Classes: None
- Top-level functions: None

## `arc/api/deps.py`

- Lines: 4
- Classes: None
- Top-level functions: startup

## `arc/api/main.py`

- Lines: 28
- Classes: None
- Top-level functions: lifespan

## `arc/api/routes.py`

- Lines: 415
- Classes: None
- Top-level functions: role_observer, role_analyst, role_operator, role_approver, role_admin, _bounded, home, health, manifest, auth_bootstrap, auth_login, auth_session, post_event, get_events, get_entities, get_entity, get_graph, timeline, post_watchlist, get_watchlists, post_case, get_cases, read_case, post_attach, get_evidence, post_proposal, post_approve, get_proposals, get_simulate, get_audit, get_receipts, verify_receipts, post_connector, get_connectors, post_poll_connector, post_note, get_notes, post_structure, get_structures, read_structure, post_structure_sensors, get_sensors, post_geofence, get_geofences, post_geo_estimate, post_demo_track, get_tracks, geo_heatmap, post_blueprint, get_blueprints, post_calibration, get_calibrations, post_import_tracks, post_incident, get_incidents

## `arc/core/__init__.py`

- Lines: 0
- Classes: None
- Top-level functions: None

## `arc/core/auth.py`

- Lines: 41
- Classes: None
- Top-level functions: require_role, make_password_hash, verify_password

## `arc/core/config.py`

- Lines: 18
- Classes: None
- Top-level functions: None

## `arc/core/db.py`

- Lines: 280
- Classes: None
- Top-level functions: connect, init_db

## `arc/core/risk.py`

- Lines: 14
- Classes: None
- Top-level functions: score_event, impact_band

## `arc/core/schemas.py`

- Lines: 200
- Classes: EventIn, EventOut, WatchlistIn, CaseIn, ProposalIn, ProposalOut, StructureIn, GeofenceIn, ObservationIn, TrackEstimateIn, BlueprintOverlayIn, CalibrationProfileIn, ImportedTrackPointIn, TrackImportIn, IncidentIn, LoginIn, ConnectorIn, NoteIn
- Top-level functions: utcnow, new_id, _validate_polygon_points

## `arc/core/simulator.py`

- Lines: 34
- Classes: None
- Top-level functions: simulate

## `arc/core/util.py`

- Lines: 31
- Classes: None
- Top-level functions: normalize_entity, guess_entity_type, fingerprint

## `arc/services/__init__.py`

- Lines: 0
- Classes: None
- Top-level functions: None

## `arc/services/audit.py`

- Lines: 88
- Classes: None
- Top-level functions: _ensure_signing_key, _encode_signature, log, append_receipt, list_receipts, verify_receipt_chain

## `arc/services/authn.py`

- Lines: 76
- Classes: None
- Top-level functions: _expires_at, ensure_bootstrap_admin, login, resolve_session

## `arc/services/bootstrap.py`

- Lines: 45
- Classes: None
- Top-level functions: seed_demo

## `arc/services/cases.py`

- Lines: 55
- Classes: None
- Top-level functions: create_case, get_case, list_cases, attach_event

## `arc/services/connectors.py`

- Lines: 134
- Classes: None
- Top-level functions: create_connector, list_connectors, get_connector, get_connector_by_name, _iter_jsonl, poll_connector, ensure_demo_connector

## `arc/services/geospatial.py`

- Lines: 468
- Classes: None
- Top-level functions: _json_load, list_structures, get_structure, create_structure, build_sensors_for_structure, list_sensors, upsert_geofence, list_geofences, infer_zone, _candidate_cloud, estimate_track, latest_tracks, get_heatmap, upsert_blueprint_overlay, list_blueprint_overlays, create_calibration_profile, list_calibration_profiles, import_track_points, create_incident, list_incidents, export_evidence_pack, generate_demo_track

## `arc/services/graph.py`

- Lines: 34
- Classes: None
- Top-level functions: upsert_edge, snapshot

## `arc/services/ingest.py`

- Lines: 96
- Classes: None
- Top-level functions: _event_count_7d, create_event, list_events

## `arc/services/notebook.py`

- Lines: 41
- Classes: None
- Top-level functions: create_note, get_note, list_notes

## `arc/services/proposals.py`

- Lines: 52
- Classes: None
- Top-level functions: create_proposal, get_proposal, approve_proposal, list_proposals

## `arc/services/resolver.py`

- Lines: 25
- Classes: None
- Top-level functions: resolve_entity

## `arc/services/watchlists.py`

- Lines: 19
- Classes: None
- Top-level functions: create_watchlist, list_watchlists

## `arc/geo/__init__.py`

- Lines: 1
- Classes: None
- Top-level functions: None

## `arc/geo/estimator.py`

- Lines: 59
- Classes: None
- Top-level functions: rssi_from_distance_meters, estimate_from_observations, make_observations

## `arc/geo/geometry.py`

- Lines: 70
- Classes: None
- Top-level functions: centroid, bounds_from_polygon, point_in_polygon, clamp_point_to_bounds, seeded, seeded_point_in_polygon, distance_meters

## `tests/__init__.py`

- Lines: 0
- Classes: None
- Top-level functions: None

## `tests/_client.py`

- Lines: 6
- Classes: None
- Top-level functions: make_transport

## `tests/conftest.py`

- Lines: 6
- Classes: None
- Top-level functions: anyio_backend

## `tests/test_arc_smoke.py`

- Lines: 62
- Classes: None
- Top-level functions: setup_module, test_health, test_event_and_graph, test_case_workflow, test_proposal_approval

## `tests/test_geo_v4_features.py`

- Lines: 67
- Classes: None
- Top-level functions: setup_module, test_blueprint_calibration_and_heatmap, test_import_evidence_and_receipts

## `tests/test_geo_workflow.py`

- Lines: 39
- Classes: None
- Top-level functions: setup_module, test_geo_seed_and_demo_track, test_manual_geo_estimate_and_geofence

## `tests/test_v5_hardening.py`

- Lines: 48
- Classes: None
- Top-level functions: setup_module, test_event_search_pushdown_and_health_version, test_case_attach_deduplicates_same_event, test_blueprint_and_calibration_upsert_stable_identity

## `tests/test_v6_ops.py`

- Lines: 49
- Classes: None
- Top-level functions: setup_module, test_auth_login_and_session, test_connector_poll_and_signed_receipts_and_notes

