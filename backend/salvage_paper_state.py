import json
import re
import shutil
from pathlib import Path

path = Path("data/paper_state.json")
backup = Path("data/paper_state_corrupt_backup.json")

shutil.copyfile(path, backup)

text = path.read_text(encoding="utf-8", errors="replace")

def extract_number(pattern, default):
    match = re.search(pattern, text)
    if not match:
        return default
    try:
        return float(match.group(1))
    except Exception:
        return default

cash = extract_number(r'"cash"\s*:\s*([0-9\.\-]+)', 10000)

decoder = json.JSONDecoder()
trades = []

for match in re.finditer(r'\{\s*"id"\s*:', text):
    start = match.start()
    try:
        obj, end = decoder.raw_decode(text[start:])
        if isinstance(obj, dict) and "id" in obj and ("entry_price" in obj or "coin_name" in obj):
            trades.append(obj)
    except Exception:
        continue

open_trades = []
closed_trades = []

seen = set()

for trade in trades:
    trade_id = trade.get("id")
    key = (trade_id, trade.get("token_address"), trade.get("opened_at"))

    if key in seen:
        continue

    seen.add(key)

    status = str(trade.get("status", "")).upper()

    if status == "OPEN":
        open_trades.append(trade)
    else:
        closed_trades.append(trade)

clean_state = {
    "cash": cash,
    "open_trades": open_trades,
    "closed_trades": closed_trades,
}

path.write_text(json.dumps(clean_state, indent=2, ensure_ascii=False), encoding="utf-8")

print("REPAIRED paper_state.json")
print("Cash:", cash)
print("Open trades:", len(open_trades))
print("Closed trades:", len(closed_trades))
print("Backup saved at:", backup)
