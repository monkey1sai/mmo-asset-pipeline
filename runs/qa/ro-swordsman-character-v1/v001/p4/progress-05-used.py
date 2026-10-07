"""Writes p4/milestone-04-progress.json after run-04 and the D decision request (run from the worktree root).

Usage: python -B runs/qa/ro-swordsman-character-v1/v001/p4/progress-05-used.py <recorded_utc> <runtime results json> <collapse classes json>
The run-01 version of the progress record is kept as milestone-04-progress-run01.json.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

P = Path("runs/qa/ro-swordsman-character-v1/v001/p4")
now, runtime_path, classes_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
run1 = json.loads((P / "run-01/merged/transition-check.json").read_text(encoding="utf-8"))
run4 = json.loads((P / "run-04/merged/transition-check.json").read_text(encoding="utf-8"))
spec = json.loads((P / "transitions-04.json").read_text(encoding="utf-8"))
runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
classes = json.loads(classes_path.read_text(encoding="utf-8"))
recheck = json.loads((P / "run-04/merged/feet-recheck.json").read_text(encoding="utf-8"))
corrected = {s["id"]: s for s in recheck["scenarios"]}
for s in run4["scenarios"]:  # the feet gate with the corrected lift rule (feet-recheck-used.py)
    s["gates"], s["pass"] = corrected[s["id"]]["gates"], corrected[s["id"]]["pass"]
    for side, f in corrected[s["id"]]["feet"].items():
        s["worst"]["feet"][side]["slide_m"] = f["slide_m"]


def by_pair(check):
    out = defaultdict(lambda: {"passed": 0, "scenarios": 0, "failing": Counter()})
    for s in check["scenarios"]:
        row = out[s["pair"]]
        row["scenarios"] += 1
        row["passed"] += s["pass"]
        row["failing"].update(k for k, ok in s["gates"].items() if not ok)
    return {k: f"{v['passed']}/{v['scenarios']}" + (f" failing {dict(v['failing'])}" if v["failing"] else "") for k, v in sorted(out.items())}


feet, contact, settles = defaultdict(float), defaultdict(float), []
for s in run4["scenarios"]:
    for side, f in s["worst"]["feet"].items():
        feet[s["pair"]] = max(feet[s["pair"]], f["slide_m"])
        contact[s["pair"]] = max(contact[s["pair"]], f["contact_slide_diagnostic_m"])
        settles += [{"id": s["id"], "side": side, "lift_mm": round(x["max_lift_m"] * 1e3, 1), "travel_mm": round(x["travel_m"] * 1e3, 1)} for x in f["settles"]]
det = runtime["determinism"]
progress = {
    "schema_version": 1, "recorded_utc": now, "milestone": 4,
    "status": f"in_progress: run-04 {sum(s['pass'] for s in run4['scenarios'])}/{len(run4['scenarios'])} scenarios pass with the decisions of entry 25; the rest fail the collapse gate at crease regions and five also the feet gate at the leg's reach (decisions D and G requested)",
    "authorization": "entries 24 (P4) and 25 (A1 B1 C1, E keep, F agreed) in runs/qa/ro-swordsman-character-v1/authorizations.json",
    "previous_record": (P / "milestone-04-progress-run01.json").as_posix(),
    "runs": {
        "run_01": {"result": (P / "run-01/merged/transition-check.json").as_posix(), "passed": f"{sum(s['pass'] for s in run1['scenarios'])}/{len(run1['scenarios'])}", "by_pair": by_pair(run1)},
        "run_02": {"result": (P / "run-02/merged/transition-check.json").as_posix(), "note": "A1 first version: a lock released when a fading-out layer lifted the foot (slides up to 40 mm) and Idle's straight knee bent sideways; superseded"},
        "run_03": {"note": "stopped at about 10:29 after the knee fix (superseded by run-04); its shard folders stay empty"},
        "run_04": {"result": (P / "run-04/merged/transition-check.json").as_posix(), "scenarios_file": (P / "transitions-04.json").as_posix(),
                   "feet_recheck": {"result": (P / "run-04/merged/feet-recheck.json").as_posix(), "script": (P / "feet-recheck-used.py").as_posix(),
                                    "why": "the stored feet gate let any lifted stance sample leave its run (meant for settle steps); it also hid locks the leg could not reach (foot lifted up to 78 mm). Corrected rule (also in the check script now): only releases and settles may lift out of a run",
                                    "stored_passed": recheck["summary"]["stored_passed"], "changed": recheck["changed"]},
                   "passed": f"{sum(s['pass'] for s in run4['scenarios'])}/{len(run4['scenarios'])}", "by_pair": by_pair(run4),
                   "script_sha256": run4["script_sha256"], "modules": run4.get("modules")},
    },
    "decisions_applied": {
        "A1": "scripts/cv1_foot_lock.py + src/cv1-foot-lock.js: lock while every leg layer has the foot in stance during a fade; held while any leg layer keeps it down; released over 0.12 s in the air; settle step (0.3 s, lift min(40 mm, half the offset)) when the remaining layer never lifts the foot; knee hinge = leg plane + 0.2 x toe-pole plane (Idle's 178 deg knee bends towards the toes); Idle->Walk enters Walk at the right foot's mid-stance (as Walk<->Run match feet)",
        "B1": "coat exemption when every bed-clip leg layer is seated (other layers neutral)",
        "C1": {"rule": "entry fades end by the target's first socket/bed event; exit fades from non-loop clips start after the last event", "changed": spec["fade_timing_changed"]},
    },
    "findings_run_04": {
        "feet_slide_worst_mm": {k: round(v * 1e3, 2) for k, v in sorted(feet.items())},
        "settle_steps": {"count": len(settles), "lift_mm_max": max((x["lift_mm"] for x in settles), default=None), "travel_mm_max": max((x["travel_mm"] for x in settles), default=None)},
        "contact_slide_diagnostic_worst_mm": {k: round(v * 1e3, 1) for k, v in sorted(contact.items())},
        "contact_diagnostic_note": "not a gate: sole near the floor whatever the stance windows say; includes the clips' own pivot turns and swing feet blended with a planted foot",
        "collapse_classes": classes["classes_by_pair"],
        "collapse_class_definitions": "foot_lock: under 5 % only with the lock; folded_in_clip: under 5 % without the lock too and some layer alone has the triangle folded or under 5 %; blend: under 5 % without the lock while every layer alone is open and above 5 %",
    },
    "runtime": {
        "results": runtime_path.as_posix(), "pass": runtime["pass"], "verdicts": runtime["verdicts"],
        "closed_loop": {"blocks": len(runtime["closed_loop"]), "max_error_um": round(max(c["max_error_m"] for c in runtime["closed_loop"]) * 1e6, 3),
                        "foot_target_max_diff_m": max(c["foot_lock"]["target_max_abs_difference_m"] for c in runtime["closed_loop"])},
        "determinism": {"comparisons": len(det), "max_m": max(max(d["play_vs_seek_m"], d["pause_resume_vs_seek_m"]) for d in det),
                        "diagnostic_mixer_time_advance_max_m": max(d["diagnostic_mixer_time_advance_vs_seek_m"] for d in det)},
        "negative_controls": {k: {"expected_failing_gate": v.get("expected_failing_gate"), "detected": v["detected"]} for k, v in runtime["negative_controls"].items()},
        "cost": runtime["cost"], "machine": runtime["runtime"],
    },
    "not_done": ["decision D (collapse at crease regions)", "Idle->Combo->Idle (combo clip: P3 remainder, not authorised)", "art review of the transitions",
                 "independent gray grasp acceptance (not planned in P4)", "commit/push (not covered by entries 24-25)"],
    "evidence_scripts": {"generator": (P / "progress-05-used.py").as_posix(), "compare": (P / "compare-runs-used.py").as_posix(),
                         "collapse_classes": (P / "classify-collapse-used.py").as_posix()},
}
target = P / "milestone-04-progress.json"
keep = P / "milestone-04-progress-run01.json"
if not keep.exists():
    keep.write_bytes(target.read_bytes())
target.write_text(json.dumps(progress, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"written": now, "status": progress["status"]}, ensure_ascii=False))
