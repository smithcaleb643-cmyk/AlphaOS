import json
import os
from datetime import datetime

from core.learning import get_learning_report

MEMORY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "learning_memory.json")
)

SNAPSHOT_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "learning_snapshots.jsonl")
)


def ensure_data_folder():
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)


def save_learning_memory(reason="manual_save"):
    ensure_data_folder()

    report = get_learning_report()

    payload = {
        "saved_at": datetime.utcnow().isoformat(),
        "reason": reason,
        "learning": report,
    }

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    with open(SNAPSHOT_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(payload) + "\n")

    return payload


def load_learning_memory():
    ensure_data_folder()

    if not os.path.exists(MEMORY_FILE):
        return {
            "saved_at": None,
            "reason": "no_saved_learning_yet",
            "learning": None,
        }

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)