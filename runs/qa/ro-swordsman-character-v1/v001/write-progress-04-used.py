"""Write v001-progress-04.json. Usage: python -B write-progress-04-used.py <now_utc>"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
now = sys.argv[1]
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
iso = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
Q = "runs/qa/ro-swordsman-character-v1/v001"
A = "assets/processed/ro-swordsman-character-v1/v001"
sweep = Q + "/b03-hands/joint-range/joint-range-result.json"
result = json.loads((ROOT / sweep).read_text(encoding="utf-8"))
report = json.loads((ROOT / Q / "b01-base/assemble-report.json").read_text(encoding="utf-8"))
closed = [354, 486, 776]
current = round((iso(now) - iso("2026-10-05T05:48:09Z")).total_seconds())
record = {
    "id": "v001", "recorded_utc": now, "request": "ro-swordsman-character-v1-r4", "status": "in progress (not in the ledger; no completion claimed)",
    "intervals_seconds": closed + [current], "interval_starts_utc": ["2026-10-05T04:57:13Z", "2026-10-05T05:07:10Z", "2026-10-05T05:21:53Z", "2026-10-05T05:48:09Z"],
    "active_seconds_total": sum(closed) + current, "trial_seconds_cap": 21600,
    "current_build": {"path": A + "/b03-hands/ro_character_v001_b03-hands.blend", "sha256": sha(A + "/b03-hands/ro_character_v001_b03-hands.blend"),
                      "rules": {"path": A + "/b03-hands/corrective-rules.json", "sha256": sha(A + "/b03-hands/corrective-rules.json")},
                      "poses": {"path": A + "/b03-hands/poses.json", "sha256": sha(A + "/b03-hands/poses.json")},
                      "chain": ["b01-base: assembly (hand material, cuff on static and twist carriers, stumps cut at -55 mm, toe weights, original left bracer cut)",
                                "b02-folds: seven one-vertex pose-driven fixes for folding core triangles", "b03-hands: 19 pose-driven hand keys per hand"],
                      "bones": report["bones"]["after"], "triangles": report["triangles_total"], "protected_r010_hand": report["protected_r010_hand"], "cuff": {k: v for k, v in report["cuff"].items() if k != "right_vertex_ids_changed"}},
    "joint_range": {"path": sweep, "sha256": sha(sweep), "contract": result["contract"], "motions": len(result["results"]), "numeric_gate_pass": result["numeric_gate_pass"],
                    "rest_gate": result["rest_gate"], "baseline_motions_failed": 34},
    "fixed_views": {view: {"path": f"{Q}/b03-hands/views/{view}.png", "sha256": sha(f"{Q}/b03-hands/views/{view}.png")} for view in ("front", "side", "back", "three-quarter", "detail")},
    "gray_review": {"sheets": Q + "/a34-hands/gray-review-ab", "subject_of_sheets": "a34-hands and the r4 baseline; b03-hands has the same geometry chain with the textured hand material",
                    "status": "independent blind A/B review running in the background at record time"},
    "not_done": ["independent gray review result and whatever it requires", "real shoulder, pauldron and coat deformation work", "16 cross-UV-island faces on the hands",
                 "all nine clips, VFX, interaction windows", "QA scene with the runtime evaluator for these rules", "GLB export with restored weights and fresh readback",
                 "negative controls, performance report, holdout", "ledger entry for this candidate"],
    "new_paid_submissions": 0,
}
with open(ROOT / Q / "v001-progress-04.json", "x", encoding="utf-8", newline=chr(10)) as handle:
    json.dump(record, handle, ensure_ascii=False, indent=1)
print(record["active_seconds_total"], record["joint_range"]["numeric_gate_pass"])
