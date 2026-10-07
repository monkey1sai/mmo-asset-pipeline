"""Writes p4/milestone-04-progress.json and p4/p4-decisions-20261006.json from the P4 evidence files (run from the worktree root).

Usage: python -B runs/qa/ro-swordsman-character-v1/v001/p4/progress-04-used.py <recorded_utc>
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

P = Path("runs/qa/ro-swordsman-character-v1/v001/p4")
now = sys.argv[1]
run = json.loads((P / "run-01/merged/transition-check.json").read_text(encoding="utf-8"))
cont = json.loads((P / "continuity-03/continuity-check.json").read_text(encoding="utf-8"))
probe = json.loads((P / "diag-03/probe.json").read_text(encoding="utf-8"))
runtime_path = P / "runtime/20261006t092518z-p4-results.json"
runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
cx = {name: json.loads((P / f"cx-01/{name}/transition-check.json").read_text(encoding="utf-8")) for name in ("clean", "weapon-in-hand", "stance-window-walk")}

feet, bed_rows, collapse_rows, weapon_rows = defaultdict(float), Counter(), Counter(), defaultdict(set)
for s in run["scenarios"]:
    for f in s["worst"]["feet"].values():
        feet[s["pair"]] = max(feet[s["pair"]], f["slide_m"])
    for r in s["rows"]:
        if "bed_clearance" in r and not r["bed_clearance"]["pass"]:
            bed_rows[s["pair"]] += 1
        if r["collapsed"]:
            collapse_rows[s["pair"]] += 1
        if r["weapon_body_m"] > 0.001 or not r["grasp"]["pass"]:
            weapon_rows[s["id"]].add(r["t"])
probes = []
for e in probe["probes"]:
    w = str(e["worst_triangle"])
    snaps = e["snapshots"]
    probes.append({"sample": f"{e['id']}@{e['t']}", "triangle": int(w), "mesh": snaps["blend"]["lowest"][0]["mesh"], "dominant": snaps["blend"]["lowest"][0]["dominant"],
                   "area_ratio_and_neighbour_agreement": {k: [v["watch_ratios"][w], v["watch_neighbour_agreement"][w]] for k, v in snaps.items()},
                   "bed_depth_by_mesh_m": {k: v["bed_depth_by_mesh_m"] for k, v in snaps.items() if v["bed_depth_by_mesh_m"]}})
cx_summary = {name: {"fault": d["fault"], "pass": d["scenarios"][0]["pass"], "failing_gates": sorted(k for k, ok in d["scenarios"][0]["gates"].items() if not ok)}
              for name, d in cx.items()}
det = runtime["determinism"]
runtime_summary = {
    "results": runtime_path.as_posix(), "pass": runtime["pass"], "verdicts": runtime["verdicts"],
    "closed_loop": {"blocks": len(runtime["closed_loop"]), "max_error_um": round(max(c["max_error_m"] for c in runtime["closed_loop"]) * 1e6, 3), "gate_um": 10},
    "determinism": {"comparisons": len(det), "max_play_or_pause_vs_seek_m": max(max(d["play_vs_seek_m"], d["pause_resume_vs_seek_m"]) for d in det), "gate_m": 1e-9,
                    "diagnostic_mixer_time_advance_max_m": max(d["diagnostic_mixer_time_advance_vs_seek_m"] for d in det)},
    "loop_seams_deg": {s["clip"]: round(s["max_bone_deg"], 3) for s in runtime["loop_seams"]},
    "negative_controls": {k: {"expected_failing_gate": v.get("expected_failing_gate"), "detected": v["detected"]} for k, v in runtime["negative_controls"].items()},
    "cost": runtime["cost"], "machine": runtime["runtime"]}

progress = {
    "schema_version": 1, "recorded_utc": now, "milestone": 4,
    "status": "in_progress: QA scene, Blender transition matrix and runtime checks run; 61/164 scenarios pass run-01; user decisions requested (p4-decisions-20261006.json) before run-02",
    "authorization": "runs/qa/ro-swordsman-character-v1/authorizations.json entry 24 (P4; no commit/push, no relaxation of any gate or exemption)",
    "done": {
        "controller": "scripts/cv1_transition.py + tools/runtime-qa/three/src/cv1-transition.js (twin; tests/test_cv1_transition.py incl. the node comparison); blended interaction states clamped to [0, 1] (weights summing to 1 + ulp)",
        "blender_matrix_run_01": {"result": "runs/qa/ro-swordsman-character-v1/v001/p4/run-01/merged/transition-check.json", "scenarios": run["summary"]["scenarios"],
                                   "passed": run["summary"]["passed"], "note": "continuity in run-01 used a superseded definition; see continuity_03"},
        "continuity_03": {"result": (P / "continuity-03/continuity-check.json").as_posix(), "summary": cont["summary"],
                          "definition": "r6 wording: fade start against the source clips, fade end against the target clips, both straight from the clips; interrupts against the pose just before"},
        "counterexamples_blender": {"scenario": "walk-castupper-walk-r-b200-s1.0", "runs": cx_summary, "expected": {"weapon-in-hand": ["grasp"], "stance-window-walk": ["feet_slide"]}},
        "runtime": runtime_summary,
        "operable_scene": "tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-01/merged/p4-manifest.json (164 scenarios, seek slider, play/pause at 30/60/120 fps, corrective toggle, whole/hands/feet cameras)",
        "playback_contract": "the controller owns an integer step clock and sets every action time from the layer frames (mixer.update(0)); mixer-advanced time lands a hair off a key, where three.js returns the raw float32 key versus a normalised slerp (1.56e-8 m), so it is reported as a diagnostic only",
    },
    "findings": {
        "feet_slide_worst_mm_by_pair": {k: round(v * 1e3, 1) for k, v in sorted(feet.items())},
        "feet_cause": "cross-fading in-place clips: the stance foot moves in clip space while its weight ramps (residual about v*D/2 plus the placement difference); Idle->LieDown and GetUp->Idle long fades overlap LieDown 16-32 / GetUp 58-73, where the two clips plant the feet at different spots",
        "bed_clearance_failing_samples_by_pair": dict(sorted(bed_rows.items())),
        "bed_cause": "probed samples: the deepest point under the bed top is SM_RO_coat at about the bed clip's own exempted depth (e.g. 168 mm in the blend vs 176 mm for LieDown alone); the seated exemption of the clip does not carry into a transition because the other layer is not seated",
        "collapse_failing_samples_by_pair": dict(sorted(collapse_rows.items())),
        "collapse_cause": "crease regions (armpits spine/upper_arm, back of the right thigh, pelvis/upper_leg): most collapsing triangles are already folded or near-degenerate in a source clip (clip checks gate area only; flips are report-only), so a blend passes through zero area; one left-armpit case is compression by the blend itself; one coat case is the corrective response to the Sleep/GetUp blend (correctives off: no collapse)",
        "weapon_grasp_failing_scenarios": {k: len(v) for k, v in sorted(weapon_rows.items())},
        "weapon_cause": "only 400 ms x 1.5 fades: the fade spans the put-down (LieDown 30) or the pick-up (GetUp 60), or blends a lying or sitting pose against the sword on the bed",
        "idle_linkage_entry_24": "the 10.6 deg Idle vs LieDown/GetUp endpoint difference is absorbed by the fades: continuity passes in every Idle->LieDown and GetUp->Idle scenario; their failures come from the causes above",
        "probes": probes,
    },
    "not_done": ["run-02 after the decisions", "extra reference points per blend x speed and for the return fade (needs the run-02 transitions.json)",
                 "Idle->Combo->Idle (combo clip not authorised: P3 remainder)", "independent gray grasp acceptance (not planned in P4)",
                 "art review of the transitions", "commit/push (not covered by entry 24)"],
    "evidence_scripts": {"generator": (P / "progress-04-used.py").as_posix()},
}
decisions = {
    "schema_version": 1, "recorded_utc": now, "status": "awaiting_user",
    "question": "P4 run-01: which remedies and rule interpretations should run-02 use?",
    "evidence": (P / "milestone-04-progress.json").as_posix(),
    "decisions": [
        {"id": "A", "topic": "feet slide in locomotion and stance-changing transitions", "recommended": "A1",
         "options": {"A1": "stance-foot lock (two-bone leg IK) in the runtime evaluator and the Blender check, verified by the same closed loop; about 2-3 h",
                     "A2": "accept the slide of in-place cross-fades as a V1 limitation (relaxes the feet gate for those pairs)",
                     "A3": "author start/stop transition clips (new clips; larger scope)"}},
        {"id": "B", "topic": "seated coat exemption inside transitions", "recommended": "B1",
         "options": {"B1": "exempt the coat when every bed-clip layer that drives the legs is inside its seated window (non-bed layers neutral): extends entries 19-20 to transitions",
                     "B2": "keep strict: those samples stay failing"}},
        {"id": "C", "topic": "fade timing around interaction events", "recommended": "C1",
         "options": {"C1": "a fade may not overlap a socket or bed-support event of either clip: entry fades finish before the target's first event, exit fades start after the source's last event (non-loop clips hold their last frame); combinations that cannot fit are shortened to fit and listed",
                     "C2": "keep the timing: the 400 ms x 1.5 combinations stay failing"}},
        {"id": "D", "topic": "collapse at crease regions", "recommended": "decide after run-02 (A and C change the leg poses and remove the long-fade cases)",
         "options": {"D1": "fix the armpit and hip-crease folds in the foundation (b21) and re-verify every clip; hours",
                     "D2": "keep the gate strict and list the remaining cases as V1 known issues",
                     "D3": "judge transition collapse only on triangles that are non-degenerate and unfolded in every active source clip at that time, listing the rest as foundation issues (gate-scope change)"}},
        {"id": "E", "topic": "interpretations to confirm", "recommended": "keep",
         "options": {"keep": "playback speed = each layer's clip time scale with blend times in real seconds; interaction states blend with the pose weights during a fade (r6's fixed 12-frame ramp governs the states inside one clip)",
                     "change": "global slow motion and/or the fixed 12-frame state ramp at transitions"}},
        {"id": "F", "topic": "budget and order", "recommended": "cap the rest of P4 at about 4 h, then decide the combo clip (P3 remainder) and P5",
         "facts": "active time 39,560 s of 64,800 s at pause-24 (25,240 s left); P3 took about twice its estimate"},
    ],
}
(P / "milestone-04-progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
(P / "p4-decisions-20261006.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("written", now)
