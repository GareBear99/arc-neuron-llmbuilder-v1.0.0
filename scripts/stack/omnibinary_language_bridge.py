#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, json, os, shutil, sqlite3, struct
from datetime import datetime, timezone
from pathlib import Path

MAGIC = b"OBINLANG1\0"
TABLES = [
    "languages",
    "language_aliases",
    "language_variants",
    "phrase_translations",
    "pronunciation_profiles",
    "phonology_profiles",
    "transliteration_profiles",
    "language_capabilities",
    "scripts",
    "source_weights",
    "self_fill_release_runs",
    "self_fill_release_artifacts",
    "self_fill_rollback_index",
]

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def export_to_omnibinary(db_path: Path, output_path: Path, manifest_path: Path | None = None) -> dict:
    db_path = db_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    payload_tables = {}
    table_hashes = {}
    table_counts = {}
    schemas = {}
    for table in TABLES:
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
        row = cur.fetchone()
        if not row:
            continue
        schemas[table] = row[0]
        cur.execute(f"SELECT * FROM {table}")
        rows = [dict(r) for r in cur.fetchall()]
        rows_bytes = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload_tables[table] = rows
        table_hashes[table] = _sha256_bytes(rows_bytes)
        table_counts[table] = len(rows)
    payload_obj = {
        "exported_at": _utc_now(),
        "db_source": str(db_path),
        "tables": payload_tables,
    }
    payload_json = json.dumps(payload_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_gz = gzip.compress(payload_json, compresslevel=9, mtime=0)
    manifest = {
        "format": "omnibinary-language-bridge-v1",
        "magic": MAGIC.decode("latin1"),
        "created_at": _utc_now(),
        "db_source": str(db_path),
        "table_counts": table_counts,
        "table_hashes": table_hashes,
        "payload_sha256": _sha256_bytes(payload_gz),
        "payload_size": len(payload_gz),
        "schemas": schemas,
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with output_path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">Q", len(manifest_bytes)))
        f.write(manifest_bytes)
        f.write(payload_gz)
    if manifest_path:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest

def import_from_omnibinary(binary_path: Path, restore_db_path: Path, report_path: Path | None = None) -> dict:
    raw = binary_path.read_bytes()
    if not raw.startswith(MAGIC):
        raise ValueError("Not an Omnibinary language bridge file")
    pos = len(MAGIC)
    manifest_len = struct.unpack(">Q", raw[pos:pos+8])[0]
    pos += 8
    manifest = json.loads(raw[pos:pos+manifest_len].decode("utf-8"))
    pos += manifest_len
    payload_gz = raw[pos:]
    payload_sha = _sha256_bytes(payload_gz)
    if payload_sha != manifest["payload_sha256"]:
        raise ValueError("Payload hash mismatch")
    payload = json.loads(gzip.decompress(payload_gz).decode("utf-8"))
    restore_db_path.parent.mkdir(parents=True, exist_ok=True)
    if restore_db_path.exists():
        restore_db_path.unlink()
    con = sqlite3.connect(str(restore_db_path))
    cur = con.cursor()
    replay_counts = {}
    for table, schema in manifest["schemas"].items():
        cur.execute(schema)
        rows = payload["tables"].get(table, [])
        if rows:
            cols = list(rows[0].keys())
            placeholders = ",".join(["?"] * len(cols))
            sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
            cur.executemany(sql, [[row.get(c) for c in cols] for row in rows])
        replay_counts[table] = len(rows)
    con.commit()
    con.close()
    report = {
        "format": manifest["format"],
        "binary_path": str(binary_path.resolve()),
        "restore_db_path": str(restore_db_path.resolve()),
        "verified_payload_sha256": payload_sha,
        "table_counts_expected": manifest["table_counts"],
        "table_counts_restored": replay_counts,
        "restored_at": _utc_now(),
        "roundtrip_ok": replay_counts == manifest["table_counts"],
    }
    if report_path:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report

def main() -> int:
    p = argparse.ArgumentParser(description="Bidirectional Omnibinary <-> language-module bridge")
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--db", required=True)
    ex.add_argument("--out", required=True)
    ex.add_argument("--manifest", required=False)
    im = sub.add_parser("import")
    im.add_argument("--binary", required=True)
    im.add_argument("--out-db", required=True)
    im.add_argument("--report", required=False)
    args = p.parse_args()
    if args.cmd == "export":
        manifest = export_to_omnibinary(Path(args.db), Path(args.out), Path(args.manifest) if args.manifest else None)
        print(json.dumps({"status":"ok","mode":"export","payload_sha256":manifest["payload_sha256"],"table_counts":manifest["table_counts"]}, indent=2))
        return 0
    report = import_from_omnibinary(Path(args.binary), Path(args.out_db), Path(args.report) if args.report else None)
    print(json.dumps({"status":"ok","mode":"import","roundtrip_ok":report["roundtrip_ok"],"table_counts_restored":report["table_counts_restored"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
