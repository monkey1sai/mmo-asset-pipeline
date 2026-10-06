"""Prepare one user-approved batch input; preserve six plans and phase accounting."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image
import workbench
from hyper3d_api import Client, read_json

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path(r"C:\Users\IOT\.codex\generated_images\01a0fc1d-f673-7ff3-bd4a-0dbfe6096075")
OPERATION = "ro-split-batch-20261003-001"
PARENT_QA = ROOT / "runs/qa/ro-swordsman-combo-r004"
QA = ROOT / "runs/qa/ro-swordsman-combo-r005"
DESIGN = ROOT / "assets/raw/ro-swordsman-combo/design-v004"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    if QA.exists() or DESIGN.exists():
        raise RuntimeError("Existing batch preparation must be preserved")
    parent = read_json(ROOT / "requests/ro-swordsman-combo-r004.json")
    clock = read_json(PARENT_QA / "phase-start.json")
    if workbench.request_sha256(parent) != clock["request_sha256"]:
        raise RuntimeError("Frozen parent request drift")
    client = Client(ROOT)
    old_plans = read_json(PARENT_QA / "generation-prepared.json")["operations"]
    for item in old_plans:
        if client.record_path(item["operation_id"]).exists() or client.private_path(item["operation_id"]).exists():
            raise RuntimeError("Reconcile previous separate-part operations before changing strategy")
        if client.plan(item["operation_id"])["plan_sha256"] != item["plan_sha256"]:
            raise RuntimeError("Separate-part plan drift")
    files = [
        ("batch-draft-01.png", "exec-d9bcd212-a34a-4542-94a8-e8549a416879.png", "rejected_input_left_margin_and_halo"),
        ("batch-draft-02.png", "exec-49679137-3caa-4b52-a26e-793a82369d2a.png", "rejected_input_halo_remains"),
        ("batch-parts.png", "exec-fc68d520-b76b-4d57-961a-883e6fccb2ca.png", "selected_white_background_complete_six_silhouettes"),
    ]
    for _, original, _ in files:
        (GENERATED / original).resolve(strict=True)
    QA.mkdir(parents=True)
    DESIGN.mkdir(parents=True)
    inventory = []
    for name, original, decision in files:
        destination = DESIGN / name
        with (GENERATED / original).open("rb") as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
        with Image.open(destination) as image:
            inventory.append({"path": destination.relative_to(ROOT).as_posix(), "sha256": sha(destination),
                "bytes": destination.stat().st_size, "size": list(image.size), "mode": image.mode,
                "decision": decision, "source": str(GENERATED / original),
                "alpha_extrema": list(image.getchannel("A").getextrema()) if image.mode == "RGBA" else None})
    save(DESIGN / "manifest.json", {"tool": "built-in image_gen", "files": inventory,
        "pixel_edits_by_script": False, "api_input": inventory[-1]["path"],
        "visual_check": "Six distinct subjects present; open hands and complete edges. White background selected after alpha halo persisted.",
        "unverified": "3D anatomy, separability, hidden surfaces and output completeness require actual generated-model inspection."})
    request = deepcopy(parent)
    request.update(id="ro-swordsman-combo-r005", title="RO 劍士：同圖六件先驗證，僅補失敗部件",
        brief="同意你的建議方案：單張分件圖先生成一次，Blender 檢查六件，僅對有證據的失敗部件補生成。")
    request["provenance"]["reference"] = "requests/ro-swordsman-combo-r005.json#brief"
    request["production"]["reason"] = "One batch input first; measure completeness, separation and repair effort before any individually justified replacement. Preserve six unsubmitted plans."
    request["assumptions"] = [x for x in request["assumptions"] if not x.startswith("Six initial") and not x.startswith("Design preparation")]
    request["assumptions"].extend([
        "One batch source generation is initially planned; six distinct editable output parts are an experiment hypothesis, not a service guarantee.",
        "Product-sheet scales intentionally differ; source scale is not anatomical fit and must be corrected in Blender.",
        "r005 changes input strategy only. r004 original start time, all spent time, three assembly revisions and unchanged time limits are carried forward; no budget reset.",
        "The two discarded raster drafts are input preparation, not completed 3D assembly candidates or art improvements.",
    ])
    request["quality"]["reference_artifacts"].append({"path": inventory[-1]["path"], "sha256": inventory[-1]["sha256"]})
    request["phase_history"] = {"previous_request": "requests/ro-swordsman-combo-r004.json",
        "previous_request_sha256": clock["request_sha256"], "previous_protocol_sha256": clock["protocol_sha256"],
        "new_method_authority": "同意你的建議方案", "accounting": "Same phase start and budget; original histories preserved.",
        "previous_six_operations": "prepared_not_submitted; held for evidence-based failures only"}
    if request["quality"]["dimensions"] != parent["quality"]["dimensions"] or request["quality"]["budget"] != parent["quality"]["budget"]:
        raise RuntimeError("Quality targets or budget changed")
    save(ROOT / "requests/ro-swordsman-combo-r005.json", request)
    stage_request = deepcopy(read_json(ROOT / "requests/ro-swordsman-combo-r004-preflight.json"))
    stage_request.update(id="ro-swordsman-combo-r005-preflight", title="RO 同圖分件：組裝／變形預檢")
    stage_request["quality"]["reference_artifacts"].append({"path": inventory[-1]["path"], "sha256": inventory[-1]["sha256"]})
    stage_request["phase_history"] = deepcopy(request["phase_history"])
    stage_request["production"]["reason"] = request["production"]["reason"]
    stage_request["assumptions"] = [x for x in stage_request["assumptions"] if not x.startswith("Six initial") and not x.startswith("Design preparation")]
    stage_request["assumptions"].append("One batch source first; preserve six unsubmitted plans. Batch preparation carries the original r004 clock and budget.")
    stage_request["assumptions"].append("Carries r004 clock and budget; stage validation cannot replace full r005 animation/effects acceptance.")
    stage_request["provenance"]["reference"] = "requests/ro-swordsman-combo-r005.json#brief"
    save(ROOT / "requests/ro-swordsman-combo-r005-preflight.json", stage_request)
    plan = workbench.production_plan(request)
    save(QA / "offline-plan.json", plan)
    save(QA / "phase-accounting.json", {"baseline_started_utc": clock["baseline_started_utc"],
        "parent_clock": "runs/qa/ro-swordsman-combo-r004/phase-start.json", "parent_clock_sha256": sha(PARENT_QA / "phase-start.json"),
        "request_sha256": workbench.request_sha256(request), "protocol_sha256": plan["quality_loop"]["protocol_sha256"],
        "budget": request["quality"]["budget"], "assembly_revision_limit": request["production"]["max_revisions"],
        "assembly_revisions_used": 0, "clock_reset": False,
        "elapsed_seconds_at_preparation": (datetime.now(timezone.utc) - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()})
    spec = {"operation_id": OPERATION, "request": "requests/ro-swordsman-combo-r005.json",
        "images": [inventory[-1]["path"]], "output_directory": "assets/raw/ro-swordsman-combo/rodin-v004/batch",
        "parameters": {"tier": "Gen-2.5-High", "mesh_mode": "Quad", "quality_override": 22000,
            "quad_normal": True, "geometry_file_format": "glb", "material": "PBR", "texture_mode": "high",
            "texture_delight": True, "TAPose": False, "is_symmetric": "unknown", "image_label": ["?"],
            "seed": 4500, "preview_render": True},
        "authorization": {"spending_scope": "Existing demand-driven monthly/regular credit authority, now one six-object image first; no top-up/upgrade. Exact global state filename remains separately subject to human authorization.",
            "credit_pool": "existing_monthly_or_regular", "no_topup_or_upgrade": True}}
    save(QA / "api-spec-batch.json", spec)
    client.prepare(spec)
    api_plan = client.plan(OPERATION)
    save(QA / "generation-prepared.json", {"operation_id": OPERATION, "state": "prepared_not_submitted",
        "plan_sha256": api_plan["plan_sha256"], "estimated_credits": api_plan["estimated_credits"],
        "global_task_file": str(client.private_path(OPERATION)), "global_file_exists_before": client.private_path(OPERATION).exists(),
        "global_write_authority": "Exact new filename pending; old six filenames not authorized by the cost question.",
        "envelope": {"destination": "https://api.hyper3d.com/api/v2/rodin", "purpose": "User-approved batch-source stress test",
            "allowed_operations": ["one generation", "same-task status", "completed download"],
            "data_transmitted": ["single six-object design image", "validated nonsecret generation parameters"],
            "forbidden_operations": ["topup", "upgrade", "secret output", "old state overwrite", "Git mutation"],
            "stop_conditions": ["missing exact-file authority", "pending/unknown submission", "collision", "unexpected destination"]}})
    print(json.dumps({"operation": OPERATION, "estimated_credits": api_plan["estimated_credits"],
        "input_sha256": inventory[-1]["sha256"], "state_file": str(client.private_path(OPERATION)), "clock_reset": False, "charged": False}))


if __name__ == "__main__":
    main()
