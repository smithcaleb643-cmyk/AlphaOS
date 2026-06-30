import json
import os
from datetime import datetime

AUDIT_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "price_audit.jsonl")
)


def ensure_data_folder():
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)


def log_price_event(event):
    ensure_data_folder()

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        **event,
    }

    with open(AUDIT_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(payload) + "\n")

    return payload


def read_recent_price_events(limit=100):
    ensure_data_folder()

    if not os.path.exists(AUDIT_FILE):
        return []

    with open(AUDIT_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    recent = lines[-limit:]
    events = []

    for line in recent:
        try:
            events.append(json.loads(line))
        except Exception:
            pass

    return events