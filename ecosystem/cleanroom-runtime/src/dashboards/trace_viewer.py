from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render_trace_html(trace: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    state = trace.get("state", {})
    events = trace.get("events", [])
    filtered = {
        "pending_confirmations": state.get("pending_confirmations", []),
        "completed_proposals": state.get("completed_proposals", []),
        "denied_proposals": state.get("denied_proposals", []),
        "plan_summaries": state.get("plan_summaries", []),
        "evaluations": state.get("evaluations", []),
        "branch_scores": state.get("branch_scores", {}),
    }
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<title>ARC Lucifer Trace Viewer</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background: #0d1117; color: #e6edf3; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; margin-bottom: 16px; }}
pre {{ white-space: pre-wrap; word-break: break-word; background: #010409; padding: 12px; border-radius: 8px; overflow: auto; }}
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 999px; background: #238636; margin-right: 8px; }}
.warn {{ background: #9e6a03; }}
.err {{ background: #da3633; }}
</style>
</head>
<body>
<h1>ARC Lucifer Trace Viewer</h1>
<div class=\"card\"><h2>Derived State</h2><pre>{html.escape(json.dumps(filtered, indent=2, sort_keys=True))}</pre></div>
<div class=\"card\"><h2>Raw State</h2><pre>{html.escape(json.dumps(state, indent=2, sort_keys=True))}</pre></div>
<div class=\"card\"><h2>Event Log</h2><pre>{html.escape(json.dumps(events, indent=2, sort_keys=True))}</pre></div>
</body>
</html>"""
    path.write_text(html_doc, encoding="utf-8")
    return path


def render_trace(kernel, output_path: str | Path) -> Path:
    trace = {
        "state": getattr(kernel.state(), "__dict__", {}),
        "events": [event.to_dict() for event in kernel.log.all()],
    }
    return render_trace_html(trace, output_path)
