"""Prepare the explicitly authorized hand/fitting phase; never submit or read secrets."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
ID = "ro-swordsman-combo-r006"
QA = ROOT / "runs/qa" / ID
DESIGN = ROOT / "assets/raw/ro-swordsman-combo/design-v006"
OPERATION = "ro-hand-source-20261003-001"
GENERATED = Path(
    r"C:\Users\IOT\.codex\generated_images\01a0fc1d-f673-7ff3-bd4a-0dbfe6096075\exec-ef4f6c70-b6d9-4729-a0fc-0990786055e6.png"
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


if QA.exists() or DESIGN.exists() or (ROOT / "requests" / (ID + ".json")).exists():
    raise RuntimeError("Preserve existing phase and design")
old = read(ROOT / "requests/ro-swordsman-combo-r005.json")
old_result = read(ROOT / "runs/qa/ro-swordsman-combo-r005/comparison-final.json")
assert old_result["next_action"] == "stop_budget" and old_result["candidate_trials_used"] == 3
old_source = read(ROOT / "runs/qa/ro-swordsman-combo-r005/v002-digit-weights/weights.json")["artifact"]
assert sha(ROOT / old_source["path"]) == old_source["sha256"]
assert GENERATED.is_file()
QA.mkdir(parents=True)
DESIGN.mkdir(parents=True)
with GENERATED.open("rb") as source, (DESIGN / "right-glove-open.png").open("xb") as target:
    shutil.copyfileobj(source, target)
image = {"path": (DESIGN / "right-glove-open.png").relative_to(ROOT).as_posix(),
         "sha256": sha(DESIGN / "right-glove-open.png")}
save(DESIGN / "manifest.json", {
    "tool": "built-in image_gen", "generated_source": str(GENERATED),
    "files": [image], "pixel_edits_by_script": False,
    "design": "One replaceable right brown leather glove; open neutral palm, five separate digits, substantial thenar root, short hollow cuff; mirror only after actual source inspection.",
    "visual_review": "Five digits and neutral palm present; wrist opening visible; no armor, sword, extra view or subject. 3D hidden surfaces and joint topology remain unverified.",
    "tool_elapsed_seconds": 19.6,
})
request = deepcopy(old)
request.update(id=ID, title="RO 劍士：獨立手套、配裝與可變形握持的新階段",
    brief="方向1；這都算是壓力測試環節，同時為了找到最佳的美術工程師的工作流、思想維度所做到訓練與成本付出")
request["provenance"]["reference"] = f"requests/{ID}.json#brief"
request["production"] = {
    "route": "split_then_generate",
    "reason": "User authorizes a new hand/fitting phase. Design one separate glove, generate a source, inspect actual anatomy/topology, refine in Blender, then test grip before full assembly and animation.",
    "max_revisions": 8,
    "reuse_candidates": ["ro-swordsman-combo-r005-v002"],
}
request["assumptions"] = [
    "User explicitly authorizes this new phase; r005 remains closed at three failed revisions with all clocks/costs/results preserved.",
    "Existing monthly/regular API spending remains demand-driven, without a new point ceiling; no top-up, upgrade, stage, commit or push.",
    "Eight 3D revisions, six hours per trial and forty-eight hours per phase are local experiment planning bounds, not API spending authorization or credit limits.",
    "This phase starts prospectively before its first 3D baseline. Earlier image planning is saved separately; its tool elapsed time is observed, total preceding planning wall time is not instrumented.",
    "The complete character, editable rig, actual300frames/60fps sequence, independent toggleable effects and BLEND/GLB acceptance remain unchanged.",
    "Generate one right glove first. Mirror source only if geometry/material handedness is suitable; do not infer rigging from Quad mode.",
    "Reuse the new core and existing equipment. A separate glove prevents cuff armor from being part of the hand skin; inspect wrist seam and hollow fitting before joining.",
    "Generated shape and texture are candidate sources. Substantial retopology, if required, is recorded as additional production effort rather than mislabeled minor polishing.",
    "Any revision needs a distinct measured hypothesis; after two failures on the same cause require new evidence or method rather than more parameter search.",
    "Repo-external private state files require exact-file authority; the new operation is prepared but not submitted until that authority is available.",
]
request["quality"]["reference_artifacts"].append(image)
request["quality"]["budget"] = {"trial_seconds": 21600, "total_seconds": 172800}
assert request["quality"]["dimensions"] == old["quality"]["dimensions"]
assert request["spec"] == old["spec"]
request["phase_history"] = {
    "previous_request": "requests/ro-swordsman-combo-r005.json",
    "previous_request_sha256": workbench.request_sha256(old),
    "previous_result": "runs/qa/ro-swordsman-combo-r005/comparison-final.json",
    "previous_result_sha256": sha(ROOT / "runs/qa/ro-swordsman-combo-r005/comparison-final.json"),
    "previous_phase_seconds": old_result["elapsed_seconds"], "previous_revisions": 3,
    "previous_phase_service_reported_credits": 1.0,
    "authority": request["brief"], "new_method": "Replaceable generated glove, separate fitting and staged functional gates",
    "old_phase_reopened": False, "quality_targets_lowered": False,
}
save(ROOT / "requests" / (ID + ".json"), request)
plan = workbench.production_plan(request)
save(QA / "offline-plan.json", plan)
save(QA / "phase-start.json", {
    "baseline_started_utc": datetime.now(timezone.utc).isoformat(),
    "clock_scope": "Prospective new 3D experimental phase, before baseline or any new paid 3D submission",
    "request_sha256": workbench.request_sha256(request),
    "protocol_sha256": workbench.quality_sha256(request),
    "budget": request["quality"]["budget"], "max_revisions": 8,
    "prior_phase_history": request["phase_history"], "baseline_source": old_source,
    "preceding_image_tool_elapsed_seconds": 19.6,
    "preceding_planning_wall_time": "not_instrumented; not represented as complete lifetime elapsed",
})
spec = {
    "operation_id": OPERATION, "request": f"requests/{ID}.json", "images": [image["path"]],
    "output_directory": "assets/raw/ro-swordsman-combo/rodin-v006/right-glove",
    "parameters": {
        "tier": "Gen-2.5-High", "mesh_mode": "Quad", "quality_override": 1000,
        "quad_normal": True, "geometry_file_format": "glb", "material": "PBR",
        "texture_mode": "high", "texture_delight": True, "TAPose": False,
        "is_symmetric": "asymmetric", "image_label": ["F"], "seed": 4601,
        "preview_render": True,
        "prompt": "One anatomically correct right brown leather glove in neutral open-hand pose, five separated digits, substantial palm and thumb root, hollow short wrist cuff. No arm, armor, weapon or additional objects.",
    },
    "authorization": {
        "spending_scope": "User authorizes direction1 hand/fitting pressure-test phase and demand-driven existing monthly/regular API credits. Exact new private state file awaits separate authority; no top-up/upgrade or Git mutation.",
        "credit_pool": "existing_monthly_or_regular", "no_topup_or_upgrade": True,
    },
}
save(QA / "api-spec-hand.json", spec)
client = Client(ROOT)
client.prepare(spec)
api_plan = client.plan(OPERATION)
save(QA / "generation-prepared.json", {
    "operation_id": OPERATION, "state": "prepared_not_submitted", "plan_sha256": api_plan["plan_sha256"],
    "estimated_credits": api_plan["estimated_credits"], "input": image,
    "global_task_file": str(client.private_path(OPERATION)),
    "global_file_exists_before": client.private_path(OPERATION).exists(),
    "global_file_authority": "Exact-file authority pending; no global write performed",
    "envelope": {
        "destination": "https://api.hyper3d.com/api/v2/rodin", "purpose": "New separate glove source for user-authorized hand/fitting phase",
        "allowed_operations": ["one generation", "same-operation status", "completed result download"],
        "data_transmitted": ["selected glove image", "validated nonsecret generation parameters"],
        "forbidden_operations": ["top-up", "upgrade", "old state overwrite", "secret output", "Git mutation"],
        "stop_conditions": ["missing exact-file authority", "unknown submission", "collision", "unexpected destination"],
    },
})
print(json.dumps({"request": ID, "operation": OPERATION, "estimated_credits": api_plan["estimated_credits"],
    "state_file": str(client.private_path(OPERATION)), "submitted": False, "old_history_preserved": True}, ensure_ascii=False))
