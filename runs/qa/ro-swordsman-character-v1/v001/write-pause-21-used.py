"""Write v001-pause-21.json from v001-pause-20.json plus the interval that started with the user's decision of entry 21.
Usage: python -B write-pause-21-used.py <now_utc>"""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
now = sys.argv[1]
iso = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
start = "2026-10-06T07:05:01Z"
previous = json.loads((HERE / "v001-pause-20.json").read_text(encoding="utf-8"))
interval = round((iso(now) - iso(start)).total_seconds())
record = dict(previous)
record["recorded_utc"] = now
record["status"] = ("paused_waiting_for_user (milestone 3 numerically complete on b20 with LieDown a08 and GetUp a02 after entry 21; "
                    "art review pending; not in the ledger; no completion claimed)")
record["intervals_seconds"] = previous["intervals_seconds"] + [interval]
record["interval_starts_utc"] = previous["interval_starts_utc"] + [start]
record["active_seconds_total"] = sum(record["intervals_seconds"])
record["clips"] = dict(previous["clips"])
record["clips"].update({
    "AN_RO_LieDown": "a08 passes on b20 (entry 21: slower end of the release; check 203 samples, runtime 6.18 um / blend 1.29 um, readback 4.62 um); a06, a07 kept",
    "AN_RO_GetUp": "a02 passes on b20 (mirror of LieDown a08; runtime 6.18 um / blend 1.56 um, readback 4.62 um); a01 kept"})
record["interval_notes"] = dict(previous["interval_notes"])
record["interval_notes"][start] = ("entry 21 recorded; hand-path measurement (a07 IK-fade swing found), drafts 20-23 (join on the free arm's wrist and elbow, "
                                   "front-loaded hand relax), LieDown a08 and GetUp a02 checks, junctions, exports, runtime closed loops, readbacks, records")
out = HERE / "v001-pause-21.json"
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"interval_seconds": interval, "active_seconds_total": record["active_seconds_total"], "cap": record["trial_seconds_cap"]}))
