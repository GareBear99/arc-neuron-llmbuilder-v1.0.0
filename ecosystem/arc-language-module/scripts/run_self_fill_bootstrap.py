from __future__ import annotations

import json
from pathlib import Path

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.self_fill import scan_self_fill_gaps, list_self_fill_candidates


def main() -> None:
    init_db()
    ingest_common_seed()
    scan = scan_self_fill_gaps()
    staged = list_self_fill_candidates(status='staged', limit=20)
    out = {
        'ok': True,
        'scan': scan,
        'sample_candidates': staged,
    }
    reports = Path('docs') / 'self_fill_bootstrap_report.json'
    reports.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': True, 'report_path': str(reports), 'candidate_count': scan['summary']['candidate_count']}, indent=2))


if __name__ == '__main__':
    main()
