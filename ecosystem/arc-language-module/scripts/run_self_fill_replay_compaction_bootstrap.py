from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.source_policy import seed_source_weights
from arc_lang.services.self_fill_retention import seed_self_fill_retention_policies, run_scheduled_self_fill_release_cycle
from arc_lang.services.self_fill_replay import build_self_fill_replay_manifest, compact_self_fill_release


def main() -> None:
    init_db()
    ingest_common_seed()
    seed_source_weights()
    seed_self_fill_retention_policies()
    signing_key = os.getenv('ARC_LANG_SIGNING_KEY')
    scheduled = run_scheduled_self_fill_release_cycle(signing_key=signing_key)
    release_run_id = scheduled['release']['release_run_id']
    replay = build_self_fill_replay_manifest(release_run_id=release_run_id)
    compact = compact_self_fill_release(release_run_id=release_run_id)
    out = ROOT / 'docs' / 'self_fill_replay_compaction_bootstrap_report.json'
    out.write_text(json.dumps({'scheduled': scheduled, 'replay': replay, 'compact': compact}, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
