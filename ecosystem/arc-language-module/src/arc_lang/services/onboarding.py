from __future__ import annotations
import json
import uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import LanguageSubmissionRequest, utcnow
from arc_lang.services.importers import _ensure_language_row, _upsert_provenance

ALLOWED_STATUSES = {"submitted", "needs_review", "approved", "rejected", "seeded_local", "accepted_local", "disputed"}


def _norm_list(values: list[str]) -> list[str]:
    out=[]
    for v in values:
        s=str(v).strip()
        if s and s not in out:
            out.append(s)
    return out


def submit_language(req: LanguageSubmissionRequest) -> dict:
    """Submit a new language for review via the onboarding workflow."""
    now = utcnow()
    submission_id = f"lsub_{uuid.uuid4().hex[:12]}"
    status = req.status if req.status in ALLOWED_STATUSES else 'submitted'
    payload = {
        'submission_id': submission_id,
        'language_id': req.language_id,
        'iso639_3': req.iso639_3,
        'name': req.name,
        'family': req.family,
        'branch': req.branch,
        'parent_language_id': req.parent_language_id,
        'aliases_json': json.dumps(_norm_list(req.aliases), ensure_ascii=False),
        'common_words_json': json.dumps(_norm_list(req.common_words), ensure_ascii=False),
        'scripts_json': json.dumps(_norm_list(req.scripts), ensure_ascii=False),
        'source_name': req.source_name,
        'source_ref': req.source_ref,
        'confidence': req.confidence,
        'notes': req.notes,
        'status': status,
        'created_at': now,
        'updated_at': now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO language_submissions (
                submission_id, language_id, iso639_3, name, family, branch, parent_language_id,
                aliases_json, common_words_json, scripts_json, source_name, source_ref,
                confidence, notes, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(payload.values()),
        )
        conn.commit()
    return {"ok": True, "submission_id": submission_id, "status": status}


def list_language_submissions(status: str | None = None) -> dict:
    """List language submissions, optionally filtered by status."""
    with connect() as conn:
        if status:
            rows=[dict(r) for r in conn.execute('SELECT * FROM language_submissions WHERE status = ? ORDER BY updated_at DESC', (status,)).fetchall()]
        else:
            rows=[dict(r) for r in conn.execute('SELECT * FROM language_submissions ORDER BY updated_at DESC').fetchall()]
    return {"ok": True, "results": rows}


def approve_language_submission(submission_id: str, status: str = 'approved') -> dict:
    """Approve a language submission, promoting it to the canonical languages table."""
    if status not in ALLOWED_STATUSES:
        return {"ok": False, "error": 'invalid_status', 'allowed_statuses': sorted(ALLOWED_STATUSES)}
    now = utcnow()
    with connect() as conn:
        row = conn.execute('SELECT * FROM language_submissions WHERE submission_id = ?', (submission_id,)).fetchone()
        if not row:
            return {"ok": False, "error": 'submission_not_found', 'submission_id': submission_id}
        conn.execute('UPDATE language_submissions SET status = ?, updated_at = ? WHERE submission_id = ?', (status, now, submission_id))
        if status in {'approved', 'accepted_local'}:
            _ensure_language_row(
                conn,
                language_id=row['language_id'],
                iso639_3=row['iso639_3'],
                name=row['name'],
                family=row['family'],
                branch=row['branch'],
                parent_language_id=row['parent_language_id'],
                aliases=json.loads(row['aliases_json']),
                common_words=json.loads(row['common_words_json']),
                now=now,
                source_name=row['source_name'],
                source_ref=row['source_ref'],
                confidence=row['confidence'],
            )
            for script_id in json.loads(row['scripts_json']):
                conn.execute('INSERT OR IGNORE INTO language_scripts (language_id, script_id) VALUES (?, ?)', (row['language_id'], script_id))
            _upsert_provenance(conn, 'language', row['language_id'], row['source_name'], row['source_ref'], row['confidence'], f"Approved language submission {submission_id}.", now)
        conn.commit()
    return {"ok": True, "submission_id": submission_id, "status": status, 'language_id': row['language_id']}


def export_language_submission_template(path: str | Path) -> dict:
    """Export a blank language submission template to a JSON file."""
    payload = {
        'language_id': 'lang:example',
        'iso639_3': 'exm',
        'name': 'Example Language',
        'family': 'Example Family',
        'branch': 'Example Branch',
        'parent_language_id': None,
        'aliases': ['Example Tongue'],
        'common_words': ['hello', 'thanks'],
        'scripts': ['Latn'],
        'source_name': 'user_submission',
        'source_ref': None,
        'confidence': 0.7,
        'notes': 'Fill in verified lineage notes and sources here.',
        'status': 'submitted',
    }
    path = Path(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'ok': True, 'path': str(path)}


def import_language_submission_json(path: str | Path) -> dict:
    """Import and submit a language from a JSON file."""
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    req = LanguageSubmissionRequest(**payload)
    return submit_language(req)
