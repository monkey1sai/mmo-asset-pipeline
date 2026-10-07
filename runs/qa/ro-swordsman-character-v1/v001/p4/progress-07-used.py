"""Writes p4/milestone-04-progress.json for run-07: the P4 matrix with Idle<->Combo (combo a07, entry 29) on the current tools.

Usage: python -B runs/qa/ro-swordsman-character-v1/v001/p4/progress-07-used.py <recorded_utc> <runtime results json> <collapse classes json>
The run-01 version of the progress record is kept as milestone-04-progress-run01.json and the run-04 version as
milestone-04-progress-run04.json.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

P = Path("runs/qa/ro-swordsman-character-v1/v001/p4")
now, runtime_path, classes_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
run1 = json.loads((P / "run-01/merged/transition-check.json").read_text(encoding="utf-8"))
run4 = json.loads((P / "run-07/merged/transition-check.json").read_text(encoding="utf-8"))
spec = json.loads((P / "transitions-05.json").read_text(encoding="utf-8"))
runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
classes = json.loads(classes_path.read_text(encoding="utf-8"))
recheck = json.loads((P / "run-07/merged/feet-recheck.json").read_text(encoding="utf-8"))
if recheck["summary"]["passed"] != recheck["summary"]["stored_passed"] or recheck["changed"]:
    raise SystemExit("RUN_05_FEET_RULE_MISMATCH")  # run-05 already carries the corrected rule; the recheck must agree


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
    "status": f"run-07 with Idle<->Combo (combo a07, entry 29): {sum(s['pass'] for s in run4['scenarios'])}/{len(run4['scenarios'])} scenarios pass; known failures per entries 26 and 29 (crease collapse, leg reach, combo guard pose, Idle->Combo long fades over the combo's first steps); art review of the combo transitions pending; not committed",
    "authorization": "entries 24-26 (P4, A1 B1 C1, D2 G1) and 29 (combo a07 closed with known failures; transitions added) in runs/qa/ro-swordsman-character-v1/authorizations.json",
    "previous_records": [(P / "milestone-04-progress-run01.json").as_posix(), (P / "milestone-04-progress-run04.json").as_posix(), (P / "milestone-04-progress-run05.json").as_posix()],
    "known_failures": {"D2": "collapse gate kept strict; crease sites recorded for the next foundation revision (see findings collapse_classes and p4-decisions-d-20261006.json)",
                       "G1": "feet gate kept strict; Run->Walk at 1.5x (100/400 ms) and the Walk<->Run repeated switch exceed the leg's reach",
                       "combo (entry 29)": "Idle->Combo and Combo->Idle: collapse at the frozen guard pose / crease regions; at 400 ms x 1.0/1.5 the entry fade spans the combo's step-out (frames 10-38) while Idle keeps both feet planted, so the lock releases onto the combo's new foot spot (130-222 mm); the 400 ms x 1.5 exit fade spans the victory release of the left hand (grasp penetration 42 mm). A stance-aware fade rule or a 40-frame Idle hold at the combo start would remove the feet/grasp cases; not done (H1)"},
    "review_sheet": (P / "milestone-04-sheet.png").as_posix(),
    "runs": {
        "run_01": {"result": (P / "run-01/merged/transition-check.json").as_posix(), "passed": f"{sum(s['pass'] for s in run1['scenarios'])}/{len(run1['scenarios'])}", "by_pair": by_pair(run1)},
        "run_02": {"result": (P / "run-02/merged/transition-check.json").as_posix(), "note": "A1 first version: a lock released when a fading-out layer lifted the foot (slides up to 40 mm) and Idle's straight knee bent sideways; superseded"},
        "run_03": {"note": "stopped at about 10:29 after the knee fix (superseded by run-04); its shard folders stay empty"},
        "run_04": {"result": (P / "run-04/merged/transition-check.json").as_posix(), "feet_recheck": (P / "run-04/merged/feet-recheck.json").as_posix(),
                   "note": "115/164 after the corrected feet rule (stored 117: the stored rule let lifted locked feet leave their runs); superseded by run-05"},
        "run_05": {"result": (P / "run-05/merged/transition-check.json").as_posix(), "note": "P4 closure before the combo: 115/164"},
        "run_06": {"note": "combo pairs only (27 scenarios, 11 pass) on transitions-05; superseded by run-07", "shards": sorted(p.as_posix() for p in (P / "run-06").glob("shard-*/transition-check.json"))},
        "run_07": {"result": (P / "run-07/merged/transition-check.json").as_posix(), "scenarios_file": (P / "transitions-05.json").as_posix(),
                   "feet_recheck_agrees": (P / "run-07/merged/feet-recheck.json").as_posix(),
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
                        "diagnostic_mixer_time_advance_vs_lock_free_seek_max_m": max(d["diagnostic_mixer_time_advance_vs_lock_free_seek_m"] for d in det)},
        "negative_controls": {k: {"expected_failing_gate": v.get("expected_failing_gate"), "detected": v["detected"]} for k, v in runtime["negative_controls"].items()},
        "cost": runtime["cost"], "machine": runtime["runtime"],
    },
    "not_done": ["foundation fix of the crease regions (D1, not chosen)", "Idle->Combo->Idle (combo clip: P3 remainder, not authorised)", "art review of the transitions (milestone-04-sheet.png)",
                 "independent gray grasp acceptance (not planned in P4)", "commit/push (not covered by entries 24-26)"],
    "evidence_scripts": {"generator": (P / "progress-07-used.py").as_posix(), "compare": (P / "compare-runs-used.py").as_posix(),
                         "collapse_classes": (P / "classify-collapse-used.py").as_posix(), "feet_recheck": (P / "feet-recheck-used.py").as_posix(),
                         "sheet": (P / "milestone-04-sheet-used.py").as_posix()},
}
target = P / "milestone-04-progress.json"
keep = P / "milestone-04-progress-run05.json"
if not keep.exists():
    keep.write_bytes(target.read_bytes())
target.write_text(json.dumps(progress, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"written": now, "status": progress["status"]}, ensure_ascii=False))
