"""需求、製作計畫、素材搜尋與交付證據核對。離線，不呼叫製作工具。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TASKS = {"static_prop", "interactive_prop", "modular_environment", "rigged_character"}
ROUTES = {"review_existing", "reuse", "modify", "generate", "split_then_generate"}
FORMATS = {"glb", "gltf", "fbx", "obj", "blend", "usd", "usdz"}
QUALITY_CONTENT_FORMATS = FORMATS | {"bin", "mtl", "png", "jpg", "jpeg", "webp", "tga", "tif", "tiff", "exr", "hdr", "psd", "zip"}
CHECKS = {
    "art_match": ("art", "造型、比例、風格與材質符合需求及參考"),
    "scale_pivot": ("technical", "實際尺寸、軸向與 pivot 符合規格"),
    "geometry_materials": ("technical", "幾何、面數、法線及指定材質要求經檢查"),
    "package_complete": ("delivery", "指定格式、相依檔案與使用說明齊全"),
}
TASK_CHECKS = {
    "static_prop": {},
    "interactive_prop": {
        "separate_parts": ("technical", "活動部件分離，旋轉中心正確"),
        "articulation": ("technical", "指定活動範圍及穿插檢查通過"),
    },
    "modular_environment": {
        "module_fit": ("technical", "模組接合邊、間隙及重用規格經檢查"),
    },
    "rigged_character": {
        "rig_mapping": ("technical", "指定骨架、權重及掛點經檢查"),
        "deformation": ("technical", "關節變形及指定動作經檢查"),
    },
}


def text_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_int(value: object) -> bool:
    return type(value) is int and value > 0


# 已棄用：codex/art-quality-loop 的 RO 腳本仍匯入下列名稱；遷移到 identity 後移除。
def request_sha256(request: dict) -> str:
    return identity.json_digest(request)


def quality_sha256(request: dict) -> str:
    return identity.json_digest(request["quality"])


def read_json(path: Path) -> object:
    # 保留舊的寬鬆行為（含頂層陣列）；新程式改用 identity.read_json。
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evidence_file(value: str, root: Path = ROOT) -> Path:
    path = identity.recorded_path(root, value)
    relative = path.relative_to(root.resolve())
    # 只讀素材及驗收儲存區；需求或參考不能使工具讀取憑證、Git 或全域設定。
    allowed = relative.parts[0:1] in {("assets",), ("deliveries",)} or relative.parts[0:2] in {
        ("runs", "qa"), ("runs", "evidence")
    }
    extensions = FORMATS | {"bin", "mtl", "png", "jpg", "jpeg", "webp", "tga", "tif", "tiff", "exr", "hdr", "psd", "zip", "md", "json", "txt"}
    if not allowed or not path.is_file() or path.suffix.lower().lstrip(".") not in extensions or path.name.startswith(".env"):
        raise ValueError("artifact must be an existing file under assets, deliveries, runs/qa or runs/evidence")
    return path


def validate_request(request: dict) -> list[str]:
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        return ["request schema_version must be 1"]
    errors: list[str] = []
    if not identity.is_asset_id(request.get("id")):
        errors.append("invalid request id")
    for key in ("title", "brief", "purpose"):
        if not text_value(request.get(key)):
            errors.append(f"{key} must be nonempty text")
    if not isinstance(request.get("task_type"), str) or request["task_type"] not in TASKS:
        errors.append("unknown task_type")
    if not isinstance(request.get("status"), str) or request["status"] not in {"draft", "specified"}:
        errors.append("status must be draft or specified")
    if request.get("project") is not None and not identity.is_asset_id(request["project"]):
        errors.append("invalid optional project")
    style = request.get("style")
    if not isinstance(style, dict) or not text_value(style.get("description")):
        errors.append("style.description missing")
    elif any(not isinstance(style.get(key), list) or any(not text_value(v) for v in style[key]) for key in ("references", "must_have", "must_not_have")):
        errors.append("style references and constraints must be text lists")
    spec = request.get("spec")
    if not isinstance(spec, dict):
        errors.append("spec missing")
    else:
        size = spec.get("size_m")
        if size is not None and (not isinstance(size, list) or len(size) != 3 or any(type(v) not in (int, float) or not 0 < v < float("inf") for v in size)):
            errors.append("size_m must be null or three finite positive dimensions")
        for key in ("target_triangles", "texture_px"):
            if spec.get(key) is not None and not positive_int(spec[key]):
                errors.append(f"invalid {key}")
        if spec.get("units") != "m" or not isinstance(spec.get("up_axis"), str) or spec["up_axis"] not in {"+X", "+Y", "+Z"} or not isinstance(spec.get("forward_axis"), str) or spec["forward_axis"] not in {"+X", "-X", "+Y", "-Y", "+Z", "-Z"}:
            errors.append("invalid units or axes")
        elif spec["up_axis"][-1] == spec["forward_axis"][-1]:
            errors.append("up_axis and forward_axis must not be collinear")
        if type(spec.get("requires_rig")) is not bool or not isinstance(spec.get("animations"), list) or any(not text_value(v) for v in spec["animations"]):
            errors.append("invalid rig or animations")
        if request.get("task_type") == "rigged_character" and spec.get("requires_rig") is not True:
            errors.append("rigged_character requires rig")
        parts = spec.get("parts")
        seen = set()
        if not isinstance(parts, list):
            errors.append("parts must be a list")
        else:
            for part in parts:
                if not isinstance(part, dict) or not identity.is_asset_id(part.get("id")) or part.get("id") in seen or not text_value(part.get("pivot")):
                    errors.append("invalid or duplicate part")
                else:
                    seen.add(part["id"])
                    motion = part.get("motion")
                    if motion is not None:
                        if not isinstance(motion, dict) or motion.get("kind") != "rotation" or not isinstance(motion.get("axis"), str) or motion["axis"] not in {"+X", "+Y", "+Z"}:
                            errors.append("invalid part motion")
                        else:
                            bounds = motion.get("range_deg")
                            if not isinstance(bounds, list) or len(bounds) != 2 or any(type(v) not in (int, float) or not -float("inf") < v < float("inf") for v in bounds) or bounds[0] >= bounds[1]:
                                errors.append("invalid part motion range")
    delivery = request.get("delivery")
    if not isinstance(delivery, dict) or not isinstance(delivery.get("scope"), str) or delivery["scope"] not in {"standalone", "target_environment"}:
        errors.append("invalid delivery scope")
    else:
        formats = delivery.get("formats")
        if not isinstance(formats, list) or not formats or any(not isinstance(v, str) or v not in FORMATS for v in formats) or len(set(formats)) != len(formats):
            errors.append("invalid delivery formats")
        target = delivery.get("target_environment")
        if delivery["scope"] == "standalone" and target is not None:
            errors.append("standalone scope must not claim a target environment")
        if delivery["scope"] == "target_environment" and (not isinstance(target, dict) or any(not text_value(target.get(key)) for key in ("name", "version", "verification_context"))):
            errors.append("target environment requires name, version and verification_context")
    source = request.get("provenance")
    if not isinstance(source, dict) or not isinstance(source.get("kind"), str) or source["kind"] not in {"user_brief", "project_source", "example"} or not text_value(source.get("reference")):
        errors.append("traceable provenance missing")
    production = request.get("production")
    if not isinstance(production, dict) or not isinstance(production.get("route"), str) or production["route"] not in ROUTES or not text_value(production.get("reason")):
        errors.append("invalid production route/reason")
    elif type(production.get("max_revisions")) is not int or production["max_revisions"] < 0 or not isinstance(production.get("reuse_candidates"), list) or any(not identity.is_asset_id(v) for v in production["reuse_candidates"]):
        errors.append("invalid revision budget or reuse candidates")
    for key in ("assumptions", "open_questions"):
        if not isinstance(request.get(key), list) or any(not text_value(v) for v in request[key]):
            errors.append(f"{key} must be a text list")
    if "quality" in request:
        errors.extend(validate_quality(request["quality"]))
    custom = request.get("additional_checks", [])
    reserved_ids = set(CHECKS) | {key for checks in TASK_CHECKS.values() for key in checks} | {"animation", "target_environment"}
    seen_checks = set()
    if not isinstance(custom, list):
        errors.append("additional_checks must be a list")
    else:
        for check in custom:
            if not isinstance(check, dict) or not identity.is_asset_id(check.get("id")) or check["id"] in reserved_ids | seen_checks or not isinstance(check.get("area"), str) or check["area"] not in {"art", "technical", "delivery", "target_environment"} or not text_value(check.get("description")):
                errors.append("invalid, duplicate or overriding additional check")
            else:
                seen_checks.add(check["id"])
    return errors


def validate_quality(quality: object) -> list[str]:
    """Optional frozen comparison contract; existing requests remain compatible."""
    if not isinstance(quality, dict) or type(quality.get("schema_version")) is not int or quality["schema_version"] != 1:
        return ["quality schema_version must be 1"]
    errors = []
    if not isinstance(quality.get("status"), str) or quality["status"] not in {"draft", "frozen"}:
        errors.append("quality status must be draft or frozen")
    protocol = quality.get("protocol")
    if not isinstance(protocol, dict):
        errors.append("quality protocol missing")
    else:
        views = protocol.get("views")
        if not isinstance(views, list) or not views or any(not identity.is_asset_id(v) for v in views) or len(set(views)) != len(views):
            errors.append("quality views must be unique IDs")
        for key in ("lighting", "background", "framing", "tool_version", "inspection_context"):
            if not text_value(protocol.get(key)):
                errors.append(f"quality protocol {key} missing")
    references = quality.get("reference_artifacts")
    if not isinstance(references, list) or not references or any(not isinstance(v, dict) or not text_value(v.get("path")) or not isinstance(v.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", v["sha256"]) for v in references):
        errors.append("quality needs reference artifacts with SHA-256")
    dimensions = quality.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append("quality dimensions missing")
    else:
        seen = set()
        for dimension in dimensions:
            if not isinstance(dimension, dict) or not identity.is_asset_id(dimension.get("id")) or dimension["id"] in seen:
                errors.append("invalid or duplicate quality dimension")
                continue
            seen.add(dimension["id"])
            if not text_value(dimension.get("criterion")) or type(dimension.get("target")) is not int or not 1 <= dimension["target"] <= 5:
                errors.append("quality dimension needs criterion and target 1..5")
            anchors = dimension.get("anchors")
            if not isinstance(anchors, list) or len(anchors) != 6 or any(not text_value(v) for v in anchors) or len(set(anchors)) != 6:
                errors.append("quality dimension needs six distinct anchors for 0..5")
    budget = quality.get("budget")
    if not isinstance(budget, dict) or not positive_int(budget.get("trial_seconds")) or not positive_int(budget.get("total_seconds")) or budget["total_seconds"] < budget["trial_seconds"]:
        errors.append("quality needs finite positive trial/total seconds budgets")
    return errors


def required_checks(request: dict) -> list[dict]:
    errors = validate_request(request)
    if errors:
        raise ValueError("; ".join(errors))
    checks = {**CHECKS, **TASK_CHECKS[request["task_type"]]}
    if request["spec"]["requires_rig"]:
        checks["rig_mapping"] = ("technical", "指定骨架、權重及掛點經檢查")
    if request["spec"]["animations"]:
        checks["animation"] = ("technical", "需求列出的所有動作經檢查")
    if request["delivery"]["scope"] == "target_environment":
        checks["target_environment"] = ("target_environment", "指定目標環境版本及情境實測通過")
    return [{"id": key, "area": area, "description": description} for key, (area, description) in checks.items()] + deepcopy(request.get("additional_checks", []))


def readiness(request: dict) -> list[str]:
    pending = list(request["open_questions"])
    if "quality" in request and request["quality"].get("status") != "frozen":
        pending.append("品質契約仍是 draft，需整理參考、評分錨點與實測條件後凍結")
    if request["status"] == "draft":
        pending.append("需求仍是 draft，需整理為 specified")
    if request["spec"].get("size_m") is None:
        pending.append("實際尺寸規格尚未制定")
    if request["spec"].get("target_triangles") is None:
        pending.append("幾何預算尚未制定")
    if request["task_type"] == "interactive_prop" and len(request["spec"]["parts"]) < 2:
        pending.append("互動物件至少需要兩個部件與 pivot 規格")
    if request["task_type"] == "interactive_prop" and not any(part.get("motion") for part in request["spec"]["parts"]):
        pending.append("互動物件的活動方式及範圍尚未制定")
    return pending


def make_draft(aid: str, brief: str, task_type: str, profile: dict | None = None) -> dict:
    if not identity.is_asset_id(aid) or not text_value(brief) or task_type not in TASKS:
        raise ValueError("invalid intake id, brief or task_type")
    if profile is not None and (not isinstance(profile, dict) or not identity.is_asset_id(profile.get("id")) or not isinstance(profile.get("defaults"), dict) or not isinstance(profile.get("constraints"), list) or any(not text_value(v) for v in profile["constraints"])):
        raise ValueError("invalid project profile")
    defaults = (profile or {}).get("defaults", {})
    return {
        "schema_version": 1, "id": aid, "title": aid, "brief": brief,
        "purpose": "依需求製作獨立資產；用途及交付承諾待整理",
        "task_type": task_type, "project": (profile or {}).get("id"), "status": "draft",
        "provenance": {"kind": "user_brief", "reference": f"requests/{aid}.json#brief"},
        "style": {"description": brief, "references": [], "must_have": [], "must_not_have": []},
        "spec": {"size_m": None, "target_triangles": None, "texture_px": defaults.get("texture_px"),
                 "units": defaults.get("units", "m"), "up_axis": defaults.get("up_axis", "+Y"), "forward_axis": defaults.get("forward_axis", "+Z"),
                 "parts": [], "requires_rig": task_type == "rigged_character", "animations": []},
        "delivery": {"scope": "standalone", "formats": ["glb"], "target_environment": None},
        "production": {"route": "review_existing", "reason": "先查素材庫，再按差距決定重用、修改、生成或拆件", "reuse_candidates": [], "max_revisions": 1},
        "additional_checks": [],
        "assumptions": ["m／+Y／+Z 與 GLB 獨立交付是可修訂預設，不表示已量測或目標引擎已驗", *(profile or {}).get("constraints", [])],
        "open_questions": ["整理用途、尺寸、面數、造型約束及必要功能；只把真正影響製作的缺項交給委託者決定"],
    }


def api_creation_plan(request: dict) -> dict:
    """Artist handoff, not an API payload or spending authorization."""
    split = request["production"]["route"] == "split_then_generate"
    parts = request["spec"]["parts"] if split else [{"id": request["id"]}]
    return {
        "owner": "art_engineer", "preferred_execution": "hyper3d_api_via_available_mcp",
        "execution_state": "not_submitted", "capability_state": "requires_current_probe",
        "authorization_state": "requires_existing_scope_check",
        "credit_pool_state": "requires_monthly_credit_evidence",
        "input_state": "requires_artist_design_and_backend_mapping", "submission_ready": False,
        "jobs": [{"subject_id": part["id"], "design_brief": {
            "purpose": request["purpose"], "style": deepcopy(request["style"]),
            "part": deepcopy(part) if split else None, "whole_asset_spec": deepcopy(request["spec"]),
        }, "prompt": None, "reference_images": [], "operation_id": None} for part in parts],
        "preparation_pending": (["拆件路徑需先定義部件"] if not parts else []) + [
            "美術工程師將需求轉成單件／單部件 prompt，逐張確認參考圖與上傳範圍",
            "核對當前工具 schema；圖生工具缺圖時先準備設計圖，不把需求文字直接當圖片輸入",
            "生成參數與最終規格分開；固定輸出無法滿足的面數、尺寸、rig、動畫由後製處理",
            "查既有 runs，保存唯一 operation ID、需求雜湊、輸入雜湊與 Authorization Envelope",
        ],
        "execution_steps": [
            "探測工具及憑證狀態，查即時餘額；分開記錄 API 能力、額度來源與花費授權",
            "沿用明確授權，核對月訂分項、單次成本、總預算及候選上限",
            "逐筆保存 prepared 操作後呼叫 API；保存任務 ID 並查同一任務",
            "完成後下載至 repo 的新 raw 版本，核對檔案與雜湊",
            "美術工程師後製、品質比較、驗收及交付歸檔",
        ],
        "unknown_submission_policy": "reconcile_original_operation_never_resubmit",
        "reconstruction_policy": {
            "trigger": "observed_structural_gap_or_postprocess_cost_exceeds_remaining_revision_budget",
            "steps": ["preserve_failed_candidate_and_evidence", "prepare_clear_reference_design", "select_available_api_by_gap", "check_existing_spending_scope", "save_new_raw_and_baseline", "blender_detail_rig_animation_and_fixed_review"],
            "api_choices": {"shape": "reference_to_3d", "fused_parts": "part_split_if_available", "material_only": "texture_only_if_available"},
            "capabilities": "probe_current_adapter_never_infer_from_vendor_docs",
            "budget": "preserve_consumed_trials_and_costs_new_phase_requires_user_scope",
            "animation": "generated_shape_does_not_supply_verified_rig_or_action_sequence",
            "automatic_paid_retry": False,
        },
        "website_policy": "credit_evidence_or_documented_fallback_only",
        "note": "這是待工程師整理的創作交接；不是可直接送出的 API payload、交易鎖或付費許可。",
    }


def production_plan(request: dict) -> dict:
    checks = required_checks(request)
    route = request["production"]["route"]
    action = {
        "review_existing": "搜尋素材庫並比較需求差距；選擇可回復的製作路徑",
        "reuse": "核對既有版本、來源與需求符合度；不新增生成",
        "modify": "保留 master，以新版本修改指定差距",
        "generate": "建立原創視覺參考及工具輸入；依已記錄的資源授權產生候選",
        "split_then_generate": "先制定各部件、pivot 與活動規格，再分別製作及組裝",
    }[route]
    result = {
        "mode": "offline_plan_only", "request_id": request["id"], "request_sha256": identity.json_digest(request),
        "project": request.get("project"), "route": route, "reason": request["production"]["reason"],
        "pending": readiness(request), "reuse_candidates": request["production"]["reuse_candidates"],
        "steps": ["理解需求與交付承諾", "制定設計、參考與可修訂預設", action,
                  "製作與需求指定的後製", "逐項記錄美術／技術／必要目標環境證據", "核對交付檔案並歸檔"],
        "needed_capabilities": {"review_existing": ["library_search"], "reuse": ["asset_inspection", "format_export"], "modify": ["mesh_edit", "format_export"], "generate": ["reference_design", "candidate_generation", "mesh_edit", "format_export"], "split_then_generate": ["part_design", "candidate_generation", "mesh_edit", "format_export"]}[route],
        "required_checks": checks, "paid_submission_authorized_by_this_plan": False,
        "note": "計畫不執行工具、不花費；客戶設定、範例及需求單都不能替代外部操作授權。",
    }
    # A static generator does not satisfy requested rig/animation work. Keep
    if route in {"generate", "split_then_generate"}:
        result["creation_workflow"] = api_creation_plan(request)
        if route == "split_then_generate" and not request["spec"]["parts"]:
            result["pending"].append("拆件生成前需定義部件")
    if route == "modify":
        # A declared alternative for an artist, never an automatic submit or
        # a budget reset after an exhausted/unknown experiment.
        result["reconstruction_fallback"] = api_creation_plan(request)["reconstruction_policy"]
    # Source generation and local articulated authoring are separate capabilities.
    # authoring and inspection explicit, while reuse only needs verification.
    needs_authoring = route in {"modify", "generate", "split_then_generate"}
    if request["spec"]["requires_rig"]:
        result["needed_capabilities"].extend(["rig_inspection", "deformation_inspection"])
        if needs_authoring:
            result["needed_capabilities"].append("rig_authoring")
    if request["spec"]["animations"]:
        result["needed_capabilities"].append("animation_inspection")
        if needs_authoring:
            result["needed_capabilities"].append("animation_authoring")
    if "quality" in request:
        result["quality_loop"] = {
            "protocol_sha256": identity.json_digest(request["quality"]),
            "max_candidate_trials": request["production"]["max_revisions"],
            "budget": deepcopy(request["quality"]["budget"]),
            "retention_rule": "no_dimension_regression_and_gain_or_required_gate_repair",
            "delivery_rule": "all_dimension_targets_and_required_checks",
            "automation": "offline_declarations_only",
        }
    return result


def check_artifact(item: dict, root: Path) -> str | None:
    if not isinstance(item, dict) or not text_value(item.get("path")) or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
        return "artifact requires path and SHA-256"
    try:
        path = evidence_file(item["path"], root)
        if identity.file_digest(path) != item["sha256"]:
            return f"artifact hash mismatch: {item['path']}"
    except (OSError, ValueError) as exc:
        return str(exc)
    return None


def _assess_contract(request: dict, evidence: dict, root: Path = ROOT) -> dict:
    checks = required_checks(request)
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    blockers = readiness(request)
    digest = identity.json_digest(request)
    if evidence.get("request_id") != request["id"] or evidence.get("request_sha256") != digest:
        blockers.append("evidence does not match current request ID/specification hash")
    registered = evidence.get("checks", {})
    if not isinstance(registered, dict):
        raise ValueError("evidence checks must be an object")
    results = []
    for check in checks:
        record = registered.get(check["id"], {})
        if not isinstance(record, dict):
            raise ValueError("check evidence must be an object")
        status = record.get("status", "not_run")
        if not isinstance(status, str) or status not in {"pass", "fail", "not_run"}:
            raise ValueError("unknown evidence status")
        issues = []
        if status != "pass":
            issues.append(f"{check['id']}: {status}")
        else:
            items = record.get("artifacts")
            if not text_value(record.get("method")) or not isinstance(items, list) or not items:
                issues.append(f"{check['id']}: pass needs method and artifact evidence")
            else:
                issues.extend(error for item in items if (error := check_artifact(item, root)))
        blockers.extend(issues)
        results.append({**check, "declared_status": status, "evidence_integrity": "valid" if status == "pass" and not issues else "not_satisfied"})
    deliverables = evidence.get("deliverables", [])
    if not isinstance(deliverables, list) or not deliverables:
        blockers.append("no delivery files registered")
        deliverables = []
    for item in deliverables:
        error = check_artifact(item, root)
        if error:
            blockers.append(error)
    actual_formats = {Path(item["path"]).suffix.lower().lstrip(".") for item in deliverables if isinstance(item, dict) and text_value(item.get("path"))}
    for fmt in request["delivery"]["formats"]:
        if fmt not in actual_formats:
            blockers.append(f"missing requested format: {fmt}")
    return {
        "mode": "evidence_contract_check_only", "request_id": request["id"], "request_sha256": digest,
        "delivery_scope": request["delivery"]["scope"], "checks": results, "blockers": blockers,
        "decision": "eligible_for_delivery_review" if not blockers else "not_ready",
        "target_environment_claim": "registered_evidence_only" if request["delivery"]["scope"] == "target_environment" else "not_requested",
        "note": "只核對已登記證據及檔案完整性；不自行判斷外觀、骨架或引擎可用，也不宣稱已交付。",
    }


def compare_quality(request: dict, ledger: dict, root: Path = ROOT) -> dict:
    """Recompute a bounded best-version history; never edit models or trust keep labels."""
    errors = validate_request(request)
    if errors or "quality" not in request:
        raise ValueError("; ".join(errors or ["request has no quality contract"]))
    quality = request["quality"]
    digest = identity.json_digest(request)
    protocol_digest = identity.json_digest(request["quality"])
    if not isinstance(ledger, dict) or type(ledger.get("schema_version")) is not int or ledger["schema_version"] != 1:
        raise ValueError("quality ledger schema_version must be 1")
    blockers = readiness(request)
    if ledger.get("request_id") != request["id"] or ledger.get("request_sha256") != digest or ledger.get("protocol_sha256") != protocol_digest:
        blockers.append("quality ledger does not match current request/protocol hash")
    for item in quality["reference_artifacts"]:
        if error := check_artifact(item, root):
            blockers.append(error)
    trials = ledger.get("trials")
    if not isinstance(trials, list):
        raise ValueError("quality trials must be a list")
    if not trials:
        blockers.append("quality baseline not recorded")
    budget = quality["budget"]
    max_trials = request["production"]["max_revisions"]
    best = None
    results = []
    seen = set()
    elapsed = 0
    terminal = False
    dimensions = {d["id"]: d for d in quality["dimensions"]}
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict) or not identity.is_asset_id(trial.get("id")) or trial["id"] in seen:
            raise ValueError("invalid or duplicate quality trial ID")
        seen.add(trial["id"])
        issues = []
        gate_failures = []
        status = trial.get("status")
        if not isinstance(status, str) or status not in {"completed", "failed", "blocked", "pending", "unknown"}:
            raise ValueError("unknown quality trial status")
        seconds = trial.get("elapsed_seconds")
        if type(seconds) not in (int, float) or not 0 <= seconds < float("inf"):
            raise ValueError("quality elapsed_seconds must be finite and nonnegative")
        elapsed += seconds
        if terminal:
            issues.append("trial recorded after a required stop")
        if index > max_trials or seconds > budget["trial_seconds"] or elapsed > budget["total_seconds"]:
            issues.append("quality experiment budget exceeded")
        expected_parent = best["id"] if best else None
        if trial.get("parent_id") != expected_parent:
            issues.append("trial parent must be the current best version")
        if index and (not text_value(trial.get("hypothesis")) or not text_value(trial.get("change"))):
            issues.append("candidate needs hypothesis and one scoped change")
        if trial.get("protocol_sha256") != protocol_digest:
            issues.append("trial comparison protocol changed")
        if not text_value(trial.get("reviewer")):
            issues.append("trial reviewer missing")
        evidence = trial.get("evidence")
        assessment = None
        scores = trial.get("scores")
        if status == "completed":
            if not isinstance(evidence, dict):
                issues.append("completed trial needs acceptance evidence")
            else:
                assessment = _assess_contract(request, evidence, root)
                contents = [item for item in evidence.get("deliverables", []) if isinstance(item, dict) and text_value(item.get("path")) and Path(item["path"]).suffix.lower().lstrip(".") in QUALITY_CONTENT_FORMATS]
                if not any(Path(v["path"]).suffix.lower().lstrip(".") in FORMATS for v in contents) or evidence.get("subject_artifacts") != contents:
                    issues.append("trial evidence must bind subject_artifacts to model and dependency deliverables")
                if evidence.get("request_id") != request["id"] or evidence.get("request_sha256") != digest:
                    issues.append("trial evidence specification changed")
                for item in evidence.get("deliverables", []):
                    if error := check_artifact(item, root):
                        issues.append(error)
                for check in assessment["checks"]:
                    record = evidence.get("checks", {}).get(check["id"], {})
                    # Baseline may fail gates; all completed trials still need actual review evidence.
                    if record.get("status") not in {"pass", "fail"} or not text_value(record.get("method")) or not isinstance(record.get("artifacts"), list) or not record["artifacts"]:
                        issues.append(f"{check['id']}: completed trial needs reviewed evidence")
                    else:
                        issues.extend(error for item in record["artifacts"] if (error := check_artifact(item, root)))
                    if check["area"] != "art" and record.get("status") == "fail":
                        gate_failures.append(check["id"])
                gate_failures.extend(issue for issue in assessment["blockers"] if issue.startswith("missing requested format:") or issue == "no delivery files registered")
            previews = trial.get("previews")
            if not isinstance(previews, dict) or set(previews) != set(quality["protocol"]["views"]):
                issues.append("trial must supply every fixed comparison view")
            else:
                for item in previews.values():
                    if not isinstance(item, dict) or not text_value(item.get("path")) or Path(item["path"]).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                        issues.append("comparison previews must be image artifacts")
                    elif error := check_artifact(item, root):
                        issues.append(error)
            if not isinstance(scores, dict) or set(scores) != set(dimensions):
                issues.append("trial scores must cover every quality dimension")
            else:
                for score in scores.values():
                    if not isinstance(score, dict) or type(score.get("value")) is not int or not 0 <= score["value"] <= 5 or not text_value(score.get("reason")):
                        issues.append("quality scores need integer 0..5 and an observed reason")
        else:
            if not text_value(trial.get("failure_reason")):
                issues.append("unfinished trial needs failure_reason")
            if index == 0 or status in {"blocked", "pending", "unknown"}:
                issues.append("baseline unavailable or operation unresolved; stop")
                terminal = True
        if issues:
            decision = "blocked"
            blockers.extend(f"{trial['id']}: {issue}" for issue in issues)
            terminal = True
        elif status == "failed":
            decision = "failed"
        elif best is None:
            best = trial
            decision = "baseline"
        elif gate_failures:
            decision = "discard"
        else:
            differences = [scores[key]["value"] - best["scores"][key]["value"] for key in dimensions]
            previous = _assess_contract(request, best["evidence"], root)
            repaired_gate = any(c["area"] != "art" and c["declared_status"] == "fail" for c in previous["checks"]) or any(issue.startswith("missing requested format:") for issue in previous["blockers"])
            if min(differences) >= 0 and max(differences) > 0:
                best = trial
                decision = "keep_for_iteration"
            elif min(differences) >= 0 and repaired_gate:
                best = trial
                decision = "keep_for_gate_repair"
            else:
                decision = "discard"
        results.append({"id": trial["id"], "decision": decision, "issues": issues, "failed_gates": gate_failures})
    target_met = bool(best) and not blockers and all(best["scores"][key]["value"] >= dimension["target"] for key, dimension in dimensions.items())
    if target_met:
        target_met = not _assess_contract(request, best["evidence"], root)["blockers"]
    exhausted = bool(trials) and (len(trials) - 1 >= max_trials or elapsed >= budget["total_seconds"])
    return {
        "mode": "declared_quality_comparison_only", "request_id": request["id"],
        "request_sha256": digest, "protocol_sha256": protocol_digest,
        "trials": results, "blockers": blockers,
        "best_trial_id": best["id"] if best else None,
        "best_content_artifacts": best["evidence"]["subject_artifacts"] if best else [],
        "quality_target_met": target_met, "elapsed_seconds": elapsed,
        "candidate_trials_used": max(0, len(trials) - 1),
        "next_action": "stop_blocked" if blockers else "delivery_review" if target_met else "stop_budget" if exhausted else "revise_current_best",
        "note": "雜湊與比較規則已核對；分數、實測及固定視角內容仍為檢查者申報，不自動證明頂尖美術或已交付。",
    }


def assess(request: dict, evidence: dict, root: Path = ROOT) -> dict:
    result = _assess_contract(request, evidence, root)
    if "quality" in request:
        item = evidence.get("quality_ledger")
        error = check_artifact(item, root)
        if error:
            result["blockers"].append(f"quality ledger: {error}")
        elif Path(item["path"]).suffix.lower() != ".json":
            result["blockers"].append("quality ledger must be a JSON artifact")
        else:
            comparison = compare_quality(request, identity.read_json(evidence_file(item["path"], root)), root)
            result["quality_comparison"] = comparison
            result["blockers"].extend(comparison["blockers"])
            if not comparison["quality_target_met"]:
                result["blockers"].append("quality targets or required best-version checks not satisfied")
            delivered_contents = [v for v in evidence.get("deliverables", []) if isinstance(v, dict) and text_value(v.get("path")) and Path(v["path"]).suffix.lower().lstrip(".") in QUALITY_CONTENT_FORMATS]
            # A package may copy identical bytes, but changed exports/textures need re-evaluation.
            signature = lambda items: sorted((Path(v["path"]).suffix.lower(), str(v.get("sha256", ""))) for v in items)
            if signature(delivered_contents) != signature(comparison["best_content_artifacts"]):
                result["blockers"].append("delivery model/dependencies do not match the evaluated best version")
        result["decision"] = "not_ready" if result["blockers"] else "eligible_for_delivery_review"
    return result


def search_library(index: dict, query: str, project: str | None = None) -> list[dict]:
    if not isinstance(index, dict) or index.get("schema_version") != 1 or not isinstance(index.get("entries"), list):
        raise ValueError("invalid library index")
    if project is not None and not identity.is_asset_id(project):
        raise ValueError("invalid project filter")
    words = query.casefold().split()
    matches = []
    for entry in index["entries"]:
        haystack = " ".join([entry["id"], entry["name"], *entry["tags"]]).casefold()
        if all(word in haystack for word in words) and (project is None or entry.get("project") == project):
            matches.append(deepcopy(entry))
    return matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="需求驅動美術工作台（離線、不生成、不扣點）")
    commands = parser.add_subparsers(dest="command", required=True)
    intake = commands.add_parser("intake")
    intake.add_argument("--id", required=True)
    intake.add_argument("--brief", required=True)
    intake.add_argument("--type", choices=sorted(TASKS), default="static_prop")
    intake.add_argument("--profile")
    intake.add_argument("--quality", action="store_true", help="附上待整理的固定品質契約草稿")
    for name in ("validate", "plan", "assess", "compare"):
        command = commands.add_parser(name)
        command.add_argument("request")
        if name == "assess":
            command.add_argument("--evidence", required=True)
        if name == "compare":
            command.add_argument("--ledger", required=True)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--project")
    args = parser.parse_args(argv)
    try:
        if args.command == "intake":
            profile = None
            if args.profile:
                if not identity.is_asset_id(args.profile):
                    raise ValueError("invalid profile id")
                profile_path = identity.command_path(ROOT, f"projects/{args.profile}.json")
                if not profile_path.is_relative_to(identity.command_path(ROOT, "projects")):
                    raise ValueError("profile must stay in projects directory")
                profile = identity.read_json(profile_path)
                if not isinstance(profile, dict) or profile.get("schema_version") != 1 or profile.get("id") != args.profile:
                    raise ValueError("profile identity mismatch")
            # 只輸出草稿，協調者以一般檔案工具保存；不默默改寫現有需求。
            result = make_draft(args.id, args.brief, args.type, profile)
            if args.quality:
                result["quality"] = identity.read_json(identity.command_path(ROOT, "templates/quality-contract.json"))
        elif args.command == "search":
            result = {"mode": "metadata_search_only", "matches": search_library(identity.read_json(identity.command_path(ROOT, "library/index.json")), args.query, args.project)}
        else:
            request = identity.read_json(identity.command_path(ROOT, args.request))
            errors = validate_request(request)
            if errors:
                raise ValueError("; ".join(errors))
            if args.command == "validate":
                result = {"status": "valid_request", "request_id": request["id"], "request_sha256": identity.json_digest(request), "pending": readiness(request), "note": "結構有效不表示已核准製作或驗收通過"}
            elif args.command == "plan":
                result = production_plan(request)
            elif args.command == "compare":
                result = compare_quality(request, identity.read_json(identity.command_path(ROOT, args.ledger)))
            else:
                result = assess(request, identity.read_json(identity.command_path(ROOT, args.evidence)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
