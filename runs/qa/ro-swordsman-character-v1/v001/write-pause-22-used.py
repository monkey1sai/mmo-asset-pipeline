"""Write v001-pause-22.json from v001-pause-21.json plus the interval that started with the user's decision of entry 22.
Usage: python -B write-pause-22-used.py <now_utc>"""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
now = sys.argv[1]
iso = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
start = "2026-10-06T07:46:30Z"
previous = json.loads((HERE / "v001-pause-21.json").read_text(encoding="utf-8"))
interval = round((iso(now) - iso(start)).total_seconds())
record = dict(previous)
record["recorded_utc"] = now
record["status"] = ("paused_waiting_for_user (milestone 3 numerically complete on b20; seat-turn speed accepted for now, entry 22; "
                    "art review pending; not in the ledger; no completion claimed)")
record["intervals_seconds"] = previous["intervals_seconds"] + [interval]
record["interval_starts_utc"] = previous["interval_starts_utc"] + [start]
record["active_seconds_total"] = sum(record["intervals_seconds"])
record["clips"] = dict(previous["clips"])
record["interval_notes"] = dict(previous["interval_notes"])
record["interval_notes"][start] = "entry 22 recorded (turn speed option a), decision record, progress update"
out = HERE / "v001-pause-22.json"
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"interval_seconds": interval, "active_seconds_total": record["active_seconds_total"], "cap": record["trial_seconds_cap"]}))
