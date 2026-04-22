from __future__ import annotations

import json
from pathlib import Path

from arc_lang.services.self_fill_sources import run_approved_source_import_bootstrap


def main() -> None:
    result = run_approved_source_import_bootstrap()
    output = Path(__file__).resolve().parents[1] / 'docs' / 'approved_self_fill_bootstrap_report.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({**result, 'report_path': str(output)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
