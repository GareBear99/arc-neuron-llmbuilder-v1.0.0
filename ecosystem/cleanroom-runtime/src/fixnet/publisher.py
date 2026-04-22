from __future__ import annotations

from typing import Any


class FixPublisher:
    """Optional remote/export channel.

    Placeholder: this runtime stays fully local/offline.
    When enabled later, this is where encrypted export or GitHub sync would live.
    """

    def publish(self, fix_payload: dict[str, Any]) -> dict[str, Any]:
        return {'status': 'disabled', 'reason': 'publisher not configured', 'fix_id': fix_payload.get('fix_id')}
