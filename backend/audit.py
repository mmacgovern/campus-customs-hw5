"""Append-only audit trail in output/audit_trail.json.

The file is always a valid JSON list. New events are appended; nothing is
ever removed. Writes go to a temp file first and then replace the original,
so a crash mid-write can't leave broken JSON behind.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from .config import AUDIT_TRAIL
from .models import AuditEvent

_lock = threading.Lock()
MAX_RESULT_CHARS = 400


def _scrub(text: str) -> str:
    """Make sure the API key can never land in the audit file."""
    key = os.environ.get("PORTKEY_API_KEY", "").strip()
    if key and key in text:
        text = text.replace(key, "[REDACTED]")
    return text


def short(value: Any, limit: int = MAX_RESULT_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = _scrub(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _load() -> list:
    if not AUDIT_TRAIL.exists() or AUDIT_TRAIL.stat().st_size == 0:
        return []
    try:
        data = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Never wipe history: keep the unreadable file aside and start a new list.
        backup = AUDIT_TRAIL.with_name(f"audit_trail.corrupt-{int(time.time())}.json")
        AUDIT_TRAIL.replace(backup)
        return []
    return data if isinstance(data, list) else [data]


def read_events() -> list[dict]:
    """All events, oldest first (the file is append-only, so order is time order)."""
    with _lock:
        if not AUDIT_TRAIL.exists() or AUDIT_TRAIL.stat().st_size == 0:
            return []
        data = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def append_event(**fields: Any) -> AuditEvent:
    """Validate one event and append it to the audit trail."""
    fields.setdefault("timestamp", datetime.now(timezone.utc))
    if fields.get("arguments") is not None:
        fields["arguments"] = json.loads(_scrub(json.dumps(fields["arguments"], default=str)))
    if fields.get("result") is not None:
        if fields.get("step_type") == "final":
            # Keep an agent's final answer whole (line breaks included) so it can be read later.
            fields["result"] = _scrub(str(fields["result"]))
        else:
            fields["result"] = short(fields["result"])
    event = AuditEvent(**fields)

    with _lock:
        AUDIT_TRAIL.parent.mkdir(parents=True, exist_ok=True)
        events = _load()
        events.append(event.model_dump(mode="json"))
        tmp = AUDIT_TRAIL.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
        for attempt in range(5):  # OneDrive can briefly lock the file while syncing
            try:
                os.replace(tmp, AUDIT_TRAIL)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.2)
    return event
