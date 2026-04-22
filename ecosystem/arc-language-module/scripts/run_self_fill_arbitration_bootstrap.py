from __future__ import annotations

import json
from pathlib import Path

from arc_lang.core.config import ROOT
from arc_lang.services.self_fill import scan_self_fill_gaps
from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.self_fill_sources import (
    stage_iso_fixture_candidates,
    stage_glottolog_fixture_candidates,
    stage_cldr_fixture_candidates,
)
from arc_lang.services.self_fill_arbitration import (
    arbitrate_self_fill_candidates,
    list_self_fill_arbitration_runs,
    promote_arbitrated_self_fill_winners,
)


def main() -> None:
    init_db()
    ingest_common_seed()
    examples = ROOT / 'examples'
    out_path = ROOT / 'docs' / 'self_fill_arbitration_bootstrap_report.json'
    result = {
        'gap_scan': scan_self_fill_gaps(stage_candidates=True),
        'iso': stage_iso_fixture_candidates(examples / 'iso6393_sample.csv'),
        'glottolog': stage_glottolog_fixture_candidates(examples / 'glottolog_sample.csv'),
        'cldr': stage_cldr_fixture_candidates(examples / 'cldr_sample.json'),
    }
    result['arbitration'] = arbitrate_self_fill_candidates(min_score=0.25)
    result['promotion'] = promote_arbitrated_self_fill_winners(min_score=0.25)
    result['runs'] = list_self_fill_arbitration_runs(limit=5)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': True, 'output_path': str(out_path), 'arbitration_run_id': result['arbitration']['arbitration_run_id'], 'promoted_count': result['promotion']['promoted_count']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
