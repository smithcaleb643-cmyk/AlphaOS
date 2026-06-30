import os
import shutil
from datetime import datetime
from pathlib import Path

data = Path("data")
archive = data / "archive_cleanup" / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
archive.mkdir(parents=True, exist_ok=True)

keep = {
    "paper_state.json",
    "learning_memory.json",
    "learning_snapshots.jsonl",
    "price_audit.jsonl",
}

moved = []

for file in data.iterdir():
    if file.is_file() and file.name not in keep:
        shutil.move(str(file), str(archive / file.name))
        moved.append(file.name)

print("Cleanup complete.")
print("Kept active files:")
for item in sorted(keep):
    print(" -", item)

print("")
print("Moved old repair/backup files:")
for item in moved:
    print(" -", item)

print("")
print("Archive folder:")
print(archive)
