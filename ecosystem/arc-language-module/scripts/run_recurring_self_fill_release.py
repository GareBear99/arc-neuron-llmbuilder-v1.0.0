from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arc_lang.core.db import init_db
from arc_lang.services.seed_ingest import ingest_common_seed
from arc_lang.services.source_policy import seed_source_weights
from arc_lang.services.self_fill_release import run_recurring_self_fill_release


def main() -> None:
    signing_key = os.getenv('ARC_LANG_SIGNING_KEY')
    init_db()
    ingest_common_seed()
    seed_source_weights()
    result = run_recurring_self_fill_release(signing_key=signing_key)
    out = ROOT / 'docs' / 'self_fill_release_bootstrap_report.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
