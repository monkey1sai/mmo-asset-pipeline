"""Write v001-pause-20.json from v001-pause-19.json plus the interval that started with the user's decision of entry 20.
Usage: python -B write-pause-20-used.py <now_utc>"""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
now = sys.argv[1]
iso = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
start = "2026-10-06T05:27:56Z"
previous = json.loads((HERE / "v001-pause-19.json").read_text(encoding="utf-8"))
interval = round((iso(now) - iso(start)).total_seconds())
record = dict(previous)
record["recorded_utc"] = now
record["status"] = ("paused_waiting_for_user (milestone 3 numerically complete on b20: check, runtime closed loop and readback for Cast a04, "
                    "LieDown a07, Sleep_Loop a04, GetUp a01; art review pending; not in the ledger; no completion claimed)")
record["intervals_seconds"] = previous["intervals_seconds"] + [interval]
record["interval_starts_utc"] = previous["interval_starts_utc"] + [start]
record["active_seconds_total"] = sum(record["intervals_seconds"])
record["clips"] = dict(previous["clips"])
record["clips"].update({
    "AN_RO_Sleep_Loop": "a04 passes on b20 (coat untucked; check 365 samples, runtime 1.032 um, readback 1.673 um); a03 kept; art review pending",
    "AN_RO_LieDown": "a07 passes on b20 (check 203 samples, runtime 6.18 um / blend 1.29 um, readback 4.62 um); a06 kept as the first b20 attempt",
    "AN_RO_GetUp": "a01 passes on b20 (mirror of LieDown a07; check 203 samples, runtime 6.18 um / blend 1.56 um, readback 4.62 um)"})
record["interval_notes"] = dict(previous["interval_notes"])
record["interval_notes"][start] = ("entry 20 recorded; LieDown a06 check; release redesign (drafts 11-19), coat seam diagnosis and the 19 deg body-right "
                                   "coat swing, Sleep a04 (untucked), seated window encoding fix, socket state-leak fixes in the clip check, export and "
                                   "runtime harness, GetUp a01 by time reversal, closed loops for LieDown/Sleep/GetUp, records and the review sheet")
out = HERE / "v001-pause-20.json"
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"interval_seconds": interval, "active_seconds_total": record["active_seconds_total"], "cap": record["trial_seconds_cap"]}))
