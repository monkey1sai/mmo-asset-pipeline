"""Record the reviewed real baseline and bind the supplementary local protocol."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT = Path(__file__).resolve().parents[1]
ID = "ro-swordsman-combo-r006"
QA = ROOT / "runs/qa" / ID


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def artifact(path):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


request = read(ROOT / "requests" / (ID + ".json"))
clock = read(QA / "phase-start.json")
baseline = read(QA / "baseline/baseline.json")
technical = read(QA / "baseline/technical-measurements.json")
assert clock["request_sha256"] == workbench.request_sha256(request)
assert technical["nominal_height_gate"] and not technical["invalid_weights"]
assert technical["exported_animation_count"] == 0
local_contract = artifact(QA / "hand-gate-contract.json")
review = {
    "reviewer": "Coordinator: actual five full-character views, right grip side, left grip palm and actual Blender measurements",
    "scores": {
        "design-intent": {"value": 3, "reason": "Young brown-haired swordsman and silver/blue/brown palette present; cuirass/clothing overlap and unusable gripping remain."},
        "silhouette": {"value": 3, "reason": "Character readable in front/side/back; sleeve-to-bracer and thigh-to-coat connections remain unstable."},
        "form-proportion": {"value": 2, "reason": "Core volume is readable but palm root folds and cuff/body/armor fitting remain incorrect in actual close views."},
        "materials": {"value": 3, "reason": "Face and major metal/cloth/leather divisions readable; hair seams, blurred gear details and clothing overlap still visible; exporter sampler warning unresolved."},
        "craft": {"value": 1, "reason": "Right grip has measured7.05mm penetration and palm-root flaps; left thumb nearest gap23.68mm. Armor intrudes at cuff and torso."},
        "use-readability": {"value": 0, "reason": "Actual GLB contains zero animations; requested skill sequence and effects absent."},
    },
    "verdict": "NO_SHIP baseline; partial rig/inventory and numeric masks do not establish playable animation",
    "fresh_roundtrip": "not_run; zero-animation source fails the required animated-input contract before a full animated roundtrip can be tested",
    "local_gate_contract": local_contract,
}
save(QA / "baseline/review.json", review)
support = [artifact(QA / "baseline" / name) for name in ["baseline.json", "technical-measurements.json", "review.json"]]
methods = {
    "art_match": ("fail", "Five actual fixed views and close-ups show cuff/torso overlaps and grip/palm-root defects. Compared to preserved references and unchanged anchors."),
    "scale_pivot": ("pass", "Actual core rest world height1.7399998903m, feet minZ0, root bone and rig translation0; Blender metres/+Z rest and standard GLB axis conversion. Planned X/Z envelope is not asserted exact."),
    "geometry_materials": ("fail", "Actual geometry/material close-ups show fitting and palm-root defects; exporter sampler warning remains unresolved. Full topology/UV/collision tests are not passed."),
    "package_complete": ("fail", "BLEND and embedded GLB baseline exist, but final complete animated/effects package does not exist. This is baseline content, not a delivery package."),
    "rig_mapping": ("pass", "Actual48 bones, one root, all character mesh armatures bound, max4 normalized influences/no invalid weights; GLB one skin/48 joints. Scope is mapping only; deformation is a separate failed gate."),
    "deformation": ("fail", "Actual open/small-curl/single-grip rendered on both hands with corrected axes; measured gaps/penetration and visible palm/cuff folding fail. Full overhead/crouch/two-hand tests are not yet run."),
    "animation": ("fail", "Actual exported document contains zero animations; requested300frames/60fps continuous sequence is missing. No full playback claimed."),
    "export-roundtrip": ("fail", "Required animated-input contract fails because the actual exported GLB has zero animation channels. Fresh GLB import/playback was not run in this baseline; no runtime importer failure is claimed."),
    "skill-effects": ("fail", "Inspected baseline scene/export contain no independent required skill effects; effects production/playback was not run."),
}
checks = {}
for item in workbench.required_checks(request):
    status, method = methods[item["id"]]
    checks[item["id"]] = {"status": status, "method": method, "artifacts": support}
    if item["id"] in ["export-roundtrip", "skill-effects"]:
        checks[item["id"]]["runtime_execution_status"] = "not_run"
        checks[item["id"]]["failure_basis"] = "Required content actually absent; not an executed runtime-test failure"
content = [{"path": item["path"], "sha256": item["sha256"]} for item in baseline["artifacts"]]
evidence = {"schema_version": 1, "request_id": ID, "request_sha256": workbench.request_sha256(request),
    "checks": checks, "deliverables": content, "subject_artifacts": content,
    "local_gate_contract": local_contract}
ended = datetime.now(timezone.utc)
trial = {
    "id": "baseline", "parent_id": None, "status": "completed",
    "started_utc": clock["baseline_started_utc"], "ended_utc": ended.isoformat(),
    "elapsed_seconds": (ended - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds(),
    "protocol_sha256": workbench.quality_sha256(request), "reviewer": review["reviewer"],
    "previews": {name: artifact(QA / "baseline" / (name + ".png")) for name in request["quality"]["protocol"]["views"]},
    "scores": review["scores"], "evidence": evidence,
}
ledger = {"schema_version": 1, "request_id": ID, "request_sha256": workbench.request_sha256(request),
    "protocol_sha256": workbench.quality_sha256(request), "local_gate_contract": local_contract,
    "trials": [trial], "phase_history": request["phase_history"]}
comparison = workbench.compare_quality(request, ledger)
assert not comparison["blockers"], comparison
assert not comparison["quality_target_met"] and comparison["candidate_trials_used"] == 0
save(QA / "baseline/evidence.json", evidence)
save(QA / "quality-ledger.json", ledger)
save(QA / "comparison-baseline.json", comparison)
save(QA / "baseline-binding.json", {
    "request_sha256": workbench.request_sha256(request),
    "quality_sha256": workbench.quality_sha256(request), "local_gate_contract": local_contract,
    "actual_baseline_report": artifact(QA / "baseline/baseline.json"),
    "source_helper": artifact(QA / "baseline/rig-helper-used.py"),
    "first_candidate_started": False,
    "note": "Local contract frozen and hash-bound before first hand candidate. Original source geometry/UV/weights and all prior failures preserved.",
})
print(json.dumps({"baseline": "recorded", "verdict": "NO_SHIP", "candidate_trials_used": 0,
    "next_action": comparison["next_action"], "local_contract_bound": True}, ensure_ascii=False))
