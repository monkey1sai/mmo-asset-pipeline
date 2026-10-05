"""Write v001-pause-03.json. Usage: python -B write-pause-03-used.py <now_utc>"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
now = sys.argv[1]
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
iso = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
interval = round((iso(now) - iso("2026-10-05T05:21:53Z")).total_seconds())
Q = "runs/qa/ro-swordsman-character-v1/v001"
A = "assets/processed/ro-swordsman-character-v1/v001"
sweep = Q + "/a15-hands/joint-range/joint-range-result.json"
result = json.loads((ROOT / sweep).read_text(encoding="utf-8"))
failed = [r["id"] for r in result["results"] if not r["pass"]]
chop = json.loads((ROOT / Q / "a17-pose/joint-range-chop/joint-range-result.json").read_text(encoding="utf-8"))["results"][0]
record = {
    "id": "v001", "paused_utc": now, "request": "ro-swordsman-character-v1-r3",
    "intervals": [{"start": "2026-10-05T04:57:13Z", "end": "2026-10-05T05:03:07Z", "seconds": 354}, {"start": "2026-10-05T05:07:10Z", "end": "2026-10-05T05:15:16Z", "seconds": 486},
                  {"start": "2026-10-05T05:21:53Z", "end": now, "seconds": interval}],
    "active_seconds_total": 840 + interval, "trial_seconds_cap": 21600,
    "status": "paused_waiting_for_user (not in the ledger; no completion or failure claimed)",
    "current_build": {"path": A + "/a15-hands/ro_character_v001_a15-hands.blend", "sha256": sha(A + "/a15-hands/ro_character_v001_a15-hands.blend"),
                      "rules": {"path": A + "/a15-hands/corrective-rules.json", "sha256": sha(A + "/a15-hands/corrective-rules.json")},
                      "chain": ["a13-toe60 (assembly: cuff 30 mm on carrier bones, stumps cut at -55 mm, toe weights 50 mm with 60 mm radius and sideways falloff, original left bracer cut)",
                                "a14-folds (six one-vertex pose-driven fixes for folding core triangles)", "a15-hands (19 pose-driven hand keys per hand: 16 crease, 2 finger clearance, 1 fist residual)"],
                      "joint_range": {"path": sweep, "sha256": sha(sweep), "contract": result["contract"]}},
    "joint_range": {"motions": len(result["results"]), "passed": len(result["results"]) - len(failed), "failed_ids": failed, "rest_gate": result["rest_gate"], "baseline_failed": 34},
    "superseded_attempts_this_interval": ["a05-relax and a09-rigid: weight edits removed the folds but raised pair counts 2 to 38 above the baseline ceilings; replaced by pose-driven one-vertex fixes",
                                          "a10-toe80, a10-toe20, a12-base: toe weight variants; a right-boot buckle needed a sideways limit with falloff",
                                          "a07-hands, a08-hands: earlier corrective stages"],
    "two_hand_pose": {"poses": A + "/a17-pose/poses.json", "status": "draft: left and right hands no longer intersect each other at 112 mm spacing; wrists are bent too far and the hands sit against the belt",
                      "diagnostic": {"typical": {k: chop["levels"]["typical"][k] for k in ("hand_self_pairs", "hand_other_new_pairs", "other_new_pairs")},
                                     "extreme_max_other_edge_ratio": chop["levels"]["extreme"]["other_edge_ratio"][1]}},
    "contract_defect_found": {"gate": "combo-two-hand-chop body ratchet",
                              "detail": "The baseline could not pose this motion, so it has no ceiling and falls to the general bound of zero new body intersections and stretch 3. "
                                        "Any pose that raises the arms inherits the baseline's shoulder behaviour (about 3,000 new pairs, stretch 12.7 here; 600 to 2,500 pairs and stretch 30 to 40 in the baseline's own arm motions).",
                              "needs": "new request version"},
    "open_work": ["tune the two-hand pose (wrist deviation, hand-to-body clearance)", "textured hand material", "independent gray review of the joint-range sheets",
                  "body deformation is only held at baseline level by the ratchet: shoulders, coat over the thighs and pauldrons still need real work for art acceptance",
                  "clips, runtime evaluator in the QA scene, export with exact weights, negative controls, holdout"],
    "new_paid_submissions": 0,
}
with open(ROOT / Q / "v001-pause-03.json", "x", encoding="utf-8", newline=chr(10)) as handle:
    json.dump(record, handle, ensure_ascii=False, indent=1)
print(record["active_seconds_total"], record["joint_range"]["passed"], failed)
