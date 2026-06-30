import json
import shutil
from pathlib import Path

path = Path("data/paper_state.json")
backup = Path("data/paper_state_pre_repair.json")

shutil.copyfile(path, backup)

raw = path.read_bytes()

text = raw.decode("utf-8", errors="replace")

data = json.loads(text)

path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

print("paper_state.json repaired and saved as valid UTF-8 JSON")
print("Backup saved at:", backup)
