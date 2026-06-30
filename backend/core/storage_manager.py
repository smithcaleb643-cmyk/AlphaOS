import json
import os
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

MAX_BACKUPS_TO_KEEP = 20
MAX_PRICE_AUDIT_EVENTS = 2000
MAX_WALLET_EVENTS = 2000
MAX_WALLET_PROFILES = 10000


def now():
    return datetime.utcnow().isoformat()


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def bytes_to_mb(size):
    return round(size / (1024 * 1024), 4)


def file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def folder_size(path):
    total = 0

    if not os.path.exists(path):
        return 0

    for root, dirs, files in os.walk(path):
        for filename in files:
            total += file_size(os.path.join(root, filename))

    return total


def list_big_files(limit=25):
    files = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        for filename in filenames:
            path = os.path.join(root, filename)
            size = file_size(path)

            if size <= 0:
                continue

            files.append(
                {
                    "path": os.path.relpath(path, PROJECT_ROOT),
                    "size_bytes": size,
                    "size_mb": bytes_to_mb(size),
                }
            )

    files.sort(key=lambda item: item["size_bytes"], reverse=True)
    return files[:limit]


def remove_pycache():
    removed_dirs = 0
    removed_files = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        for dirname in list(dirs):
            if dirname == "__pycache__":
                path = os.path.join(root, dirname)

                try:
                    for py_root, py_dirs, py_files in os.walk(path):
                        removed_files += len(py_files)

                    shutil.rmtree(path)
                    removed_dirs += 1
                except Exception as error:
                    print("PYCACHE REMOVE FAILED:", path, error)

    return {
        "removed_dirs": removed_dirs,
        "removed_files": removed_files,
    }


def prune_backups(max_backups=MAX_BACKUPS_TO_KEEP):
    ensure_dirs()

    if not os.path.exists(BACKUP_DIR):
        return {"deleted": 0, "kept": 0}

    backups = []

    for filename in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, filename)

        if not os.path.isfile(path):
            continue

        backups.append(
            {
                "path": path,
                "filename": filename,
                "modified": os.path.getmtime(path),
                "size": file_size(path),
            }
        )

    backups.sort(key=lambda item: item["modified"], reverse=True)

    keep = backups[:max_backups]
    delete = backups[max_backups:]

    deleted = 0
    freed = 0

    for item in delete:
        try:
            freed += item["size"]
            os.remove(item["path"])
            deleted += 1
        except Exception as error:
            print("BACKUP DELETE FAILED:", item["path"], error)

    return {
        "deleted": deleted,
        "kept": len(keep),
        "freed_mb": bytes_to_mb(freed),
    }


def safe_load_json(path):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print("JSON LOAD FAILED:", path, error)
        return None


def safe_save_json(path, data):
    temp_file = path + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    with open(temp_file, "r", encoding="utf-8") as file:
        json.load(file)

    os.replace(temp_file, path)


def trim_price_audit():
    """
    Trims likely price audit JSON files.

    This is intentionally cautious because file names may change.
    It only trims JSON files that look like price audit/event logs.
    """
    if not os.path.exists(DATA_DIR):
        return {"trimmed": False, "message": "No data folder."}

    candidates = []

    for filename in os.listdir(DATA_DIR):
        lower = filename.lower()

        if not filename.endswith(".json"):
            continue

        if "price" in lower and ("audit" in lower or "event" in lower or "log" in lower):
            candidates.append(os.path.join(DATA_DIR, filename))

    results = []

    for path in candidates:
        data = safe_load_json(path)

        if data is None:
            continue

        before_size = file_size(path)
        before_events = None
        after_events = None

        if isinstance(data, list):
            before_events = len(data)

            if len(data) > MAX_PRICE_AUDIT_EVENTS:
                data = data[-MAX_PRICE_AUDIT_EVENTS:]
                after_events = len(data)
                safe_save_json(path, data)

        elif isinstance(data, dict):
            for key in ["events", "price_events", "logs"]:
                if isinstance(data.get(key), list):
                    before_events = len(data[key])

                    if len(data[key]) > MAX_PRICE_AUDIT_EVENTS:
                        data[key] = data[key][-MAX_PRICE_AUDIT_EVENTS:]
                        after_events = len(data[key])
                        data["trimmed_at"] = now()
                        safe_save_json(path, data)

                    break

        after_size = file_size(path)

        results.append(
            {
                "file": os.path.relpath(path, PROJECT_ROOT),
                "before_events": before_events,
                "after_events": after_events if after_events is not None else before_events,
                "freed_mb": bytes_to_mb(max(0, before_size - after_size)),
            }
        )

    return {
        "trimmed": True,
        "files": results,
    }


def trim_wallet_memory():
    path = os.path.join(DATA_DIR, "wallet_memory.json")

    data = safe_load_json(path)

    if not isinstance(data, dict):
        return {"trimmed": False, "message": "wallet_memory.json not found or invalid."}

    before_size = file_size(path)

    events = data.get("events", [])
    if isinstance(events, list) and len(events) > MAX_WALLET_EVENTS:
        data["events"] = events[-MAX_WALLET_EVENTS:]

    wallets = data.get("wallets", {})
    if isinstance(wallets, dict) and len(wallets) > MAX_WALLET_PROFILES:
        sorted_wallets = sorted(
            wallets.items(),
            key=lambda item: (
                float(item[1].get("trust_score") or 0),
                int(item[1].get("times_seen") or 0),
            ),
            reverse=True,
        )

        data["wallets"] = dict(sorted_wallets[:MAX_WALLET_PROFILES])

    data["last_storage_trim_at"] = now()
    safe_save_json(path, data)

    after_size = file_size(path)

    return {
        "trimmed": True,
        "events_before": len(events) if isinstance(events, list) else 0,
        "events_after": len(data.get("events", [])),
        "wallets_after": len(data.get("wallets", {})),
        "freed_mb": bytes_to_mb(max(0, before_size - after_size)),
    }


def summarize_storage():
    ensure_dirs()

    return {
        "project_root": PROJECT_ROOT,
        "backend_mb": bytes_to_mb(folder_size(BACKEND_DIR)),
        "data_mb": bytes_to_mb(folder_size(DATA_DIR)),
        "backups_mb": bytes_to_mb(folder_size(BACKUP_DIR)),
        "biggest_files": list_big_files(limit=20),
    }


def cleanup_storage():
    before = summarize_storage()

    pycache = remove_pycache()
    backups = prune_backups()
    price_audit = trim_price_audit()
    wallet_memory = trim_wallet_memory()

    after = summarize_storage()

    return {
        "ok": True,
        "ran_at": now(),
        "before": before,
        "after": after,
        "actions": {
            "pycache": pycache,
            "backups": backups,
            "price_audit": price_audit,
            "wallet_memory": wallet_memory,
        },
    }
