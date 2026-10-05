"""Prepare the user-approved split generation route; never submit or write globals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
ID = "ro-swordsman-combo-r004"
QA = ROOT / "runs/qa" / ID
DESIGN = ROOT / "assets/raw/ro-swordsman-combo/design-v003"
SOURCE = Path(r"C:\Users\IOT\.codex\generated_images\01a0fc1d-f673-7ff3-bd4a-0dbfe6096075")
PARTS = [
    ("core", "exec-f1f4b0f0-7014-4482-a5c7-0929b161c636.png", "Quad", 12000, "F", "symmetric"),
    ("cuirass", "exec-06f87ce7-15e1-4cf6-bf6c-9471369dfb17.png", "Raw", 3000, "FL", "balanced"),
    ("pauldron", "exec-da7ff1a0-8e0b-42f2-b4f9-070ab4fcac82.png", "Raw", 2000, "FL", "asymmetric"),
    ("bracer", "exec-29131490-cffd-4ca9-b1d1-688d7cc7a307.png", "Raw", 2000, "FL", "asymmetric"),
    ("coat", "exec-43525a62-12db-4fdd-8673-843e2645a424.png", "Raw", 5000, "F", "balanced"),
    ("sword", "exec-4ece3d78-d8a8-4c0c-95f8-d26ac29d7cbb.png", "Raw", 1500, "F", "symmetric"),
]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


if QA.exists() or DESIGN.exists() or (ROOT / "requests" / f"{ID}.json").exists():
    raise RuntimeError("Existing new phase must be preserved; do not overwrite or reset")
if any(not (SOURCE / name).is_file() for _, name, *_ in PARTS):
    raise RuntimeError("All six design files must exist before preparing anything")
QA.mkdir(parents=True)
DESIGN.mkdir(parents=True)
manifest = []
for part, filename, *_ in PARTS:
    target = DESIGN / f"{part}.png"
    with (SOURCE / filename).open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    manifest.append({"part": part, "path": target.relative_to(ROOT).as_posix(),
                     "bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                     "source": str(SOURCE / filename), "generation": "built-in image_gen"})
save(DESIGN / "manifest.json", {"schema_version": 1, "files": manifest})

request = deepcopy(workbench.read_json(ROOT / "requests/ro-swordsman-combo-r003.json"))
request.update(id=ID, title="RO 劍士：設計主導的分件生成與組裝", brief="我同意，但是你負責設計，給hyper3d產生，並用blender微調，")
request["production"].update(route="split_then_generate", max_revisions=3, reuse_candidates=[],
    reason="User approves design-led production. Generate unarmored character core, independent cuirass/pauldron/bracer/cloth/sword. Rigid armor avoids fused soft skin; inspect native hands and cloth before refinement. Preserve all prior source, failures and budgets.")
request["quality"]["reference_artifacts"] += [{"path": x["path"], "sha256": x["sha256"]} for x in manifest]
request["quality"]["budget"] = {"trial_seconds": 21600, "total_seconds": 64800}
request["phase_history"] = {"previous_request": "requests/ro-swordsman-combo-r003.json",
    "previous_ledger": "runs/qa/ro-swordsman-combo-r003/quality-ledger.json",
    "previous_result": "NO_SHIP/discard,1of1; preserved unchanged", "new_method_authority": request["brief"],
    "reason_for_new_phase": "New user-approved split source generation and production structure, not retroactive rescore or lowered full delivery targets."}
request["assumptions"] = ["Standalone BLEND/GLB; no game integration, stage, commit or push.",
    "Existing monthly/regular credits and demand-driven API use already explicitly authorized; no top-up or upgrade.",
    "Six initial distinct part generations are planned operations, not six blind retries. Unknown/pending submission is reconciled first.",
    "Three assembly revisions form the declared evaluation batch; new methods require new evidence and preserved histories.",
    "Left armor derives from mirrored right source; source topology, hollow interiors and finger anatomy require actual inspection.",
    "Images guide appearance; API does not guarantee clean topology, automatic rigging or animation.",
    "Full final quality targets remain four in every dimension and all requested300frames/60fps, skills and effects remain mandatory.",
    "Design preparation happened before this baseline clock; generation, assembly and review wall time will be recorded."]
request["provenance"] = {"kind": "user_brief", "reference": f"requests/{ID}.json#brief"}
errors = workbench.validate_request(request)
if errors:
    raise RuntimeError(errors)
save(ROOT / "requests" / f"{ID}.json", request)

stage = deepcopy(request)
stage.update(id=ID + "-preflight", title="RO 分件角色：組裝與變形階段驗收",
    purpose="Stage-only assembled character and functional stress poses. Passing this stage does not satisfy final continuous animation or delivery.")
stage["spec"]["animations"] = []
stage["spec"].pop("animation_contract", None)
stage["additional_checks"] = [
    {"id": "rigid-armor", "area": "technical", "description": "甲片保持剛性、接合和遮蔽表面完整；抬臂與下劈實測。"},
    {"id": "grip-contact", "area": "technical", "description": "單／雙手實際指掌至劍柄接觸及腕掌體积；不得只核對控制器坐標。"},
    {"id": "cloth-clearance", "area": "technical", "description": "站立、深蹲、下劈時衣片與腿部有足夠活動空間。"},
    {"id": "stage-export", "area": "technical", "description": "乾淨GLB重匯入及短姿勢測試，與完整連段匯出驗收分開。"}]
stage["quality"]["protocol"]["inspection_context"] = "Same fixed studio and five views. Actual open/grip/overhead/downslash/deep-crouch stress poses with no effects. This stage does not evaluate or pass full300frames or skill effects."
for dim in stage["quality"]["dimensions"]:
    if dim["id"] == "use-readability":
        dim["criterion"] = "本階段各壓力姿勢、單／雙手握持、硬甲保形及衣料讓位清楚；只代表變形階段可用，不能替代最終連段。"
        dim["anchors"] = ["壓力姿勢不能成立", "多數功能不能成立", "部分姿勢成立但有關鍵缺陷", "大部分姿勢成立仍有局部差距", "所有階段壓力姿勢與握持可用", "各階段功能精緻且穩定"]
stage["provenance"]["reference"] = f"requests/{ID}.json#brief"
errors = workbench.validate_request(stage)
if errors:
    raise RuntimeError(errors)
save(ROOT / "requests" / f"{stage['id']}.json", stage)
save(QA / "phase-start.json", {"baseline_started_utc": datetime.now(timezone.utc).isoformat(),
    "request_sha256": workbench.request_sha256(request), "protocol_sha256": workbench.quality_sha256(request),
    "history": "Previous phases retain original time/count/scores. This new user-approved source starts a declared new batch."})

client = Client(ROOT)
operations = []
for part, _, mode, faces, label, symmetry in PARTS:
    operation = f"ro-split-{part}-20261003-001"
    spec = {"operation_id": operation, "request": f"requests/{ID}.json",
        "images": [f"assets/raw/ro-swordsman-combo/design-v003/{part}.png"],
        "output_directory": f"assets/raw/ro-swordsman-combo/rodin-v003/{part}",
        "parameters": {"tier": "Gen-2.5-High", "mesh_mode": mode, "quality_override": faces,
            "quad_normal": mode == "Quad", "geometry_file_format": "glb", "material": "PBR",
            "texture_mode": "high", "texture_delight": True, "TAPose": part == "core",
            "is_symmetric": symmetry, "image_label": [label], "seed": 4400 + len(operations), "preview_render": True},
        "authorization": {"spending_scope": "User explicitly permits demand-driven existing monthly/regular API credits and now approves design->Hyper3D->Blender production. Global writes require separate exact-file authority; commit/push held.",
            "credit_pool": "existing_monthly_or_regular", "no_topup_or_upgrade": True}}
    path = QA / f"api-spec-{part}.json"
    save(path, spec)
    client.prepare(spec)
    plan = client.plan(operation)
    operations.append({"part": part, "operation_id": operation,
        "estimated_credits": plan["estimated_credits"], "plan_sha256": plan["plan_sha256"],
        "global_task_file": str(client.private_path(operation)), "global_file_exists_before": client.private_path(operation).exists(),
        "status": "prepared_not_submitted", "output_directory": spec["output_directory"]})
save(QA / "generation-prepared.json", {"operations": operations, "estimated_initial_credits": sum(x["estimated_credits"] for x in operations),
    "spending_authority": "Already granted; no new points approval requested.", "global_write_authority": "Awaiting exact six new task files; old single-task authority does not cover new operations.",
    "envelope": {"destination": "https://api.hyper3d.com/api/v2/rodin", "purpose": "Six specified designed parts for one RO character",
        "allowed_operations": ["one initial generation per prepared part", "same-task status", "completed result download"],
        "data_transmitted": ["six new design images, one per operation", "validated nonsecret generation parameters"],
        "forbidden_operations": ["topup", "upgrade", "secret output", "old state overwrite", "Git mutation"],
        "stop_conditions": ["unknown/pending submission", "unexpected destination", "file collision", "global write authority missing"]}})
save(QA / "offline-plan.json", workbench.production_plan(request))
print(json.dumps({"request_id": ID, "designs": len(manifest), "prepared": operations}, ensure_ascii=False))
