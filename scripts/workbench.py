"""需求、製作計畫、素材搜尋與交付證據核對。離線，不呼叫製作工具。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
TASKS = {"static_prop", "interactive_prop", "modular_environment", "rigged_character"}
ROUTES = {"review_existing", "reuse", "modify", "generate", "split_then_generate"}
FORMATS = {"glb", "gltf", "fbx", "obj", "blend", "usd", "usdz"}
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


def safe_id(value: object) -> bool:
    return isinstance(value, str) and bool(ID.fullmatch(value)) and ".." not in value


def text_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def local_path(value: str, root: Path = ROOT) -> Path:
    root = root.resolve()
    path = Path(value)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("path must stay inside this repository")
    return path


def evidence_file(value: str, root: Path = ROOT) -> Path:
    path = local_path(value, root)
    relative = path.relative_to(root.resolve())
    # 只讀素材及驗收儲存區；需求或參考不能使工具讀取憑證、Git 或全域設定。
    allowed = relative.parts[0:1] in {("assets",), ("deliveries",)} or relative.parts[0:2] in {
        ("runs", "qa"), ("runs", "evidence")
    }
    extensions = FORMATS | {"bin", "mtl", "png", "jpg", "jpeg", "webp", "tga", "tif", "tiff", "exr", "hdr", "psd", "zip", "md", "json", "txt"}
    if not allowed or not path.is_file() or path.suffix.lower().lstrip(".") not in extensions or path.name.startswith(".env"):
        raise ValueError("artifact must be an existing file under assets, deliveries, runs/qa or runs/evidence")
    return path


def request_sha256(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def validate_request(request: dict) -> list[str]:
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        return ["request schema_version must be 1"]
    errors: list[str] = []
    if not safe_id(request.get("id")):
        errors.append("invalid request id")
    for key in ("title", "brief", "purpose"):
        if not text_value(request.get(key)):
            errors.append(f"{key} must be nonempty text")
    if not isinstance(request.get("task_type"), str) or request["task_type"] not in TASKS:
        errors.append("unknown task_type")
    if not isinstance(request.get("status"), str) or request["status"] not in {"draft", "specified"}:
        errors.append("status must be draft or specified")
    if request.get("project") is not None and not safe_id(request["project"]):
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
                if not isinstance(part, dict) or not safe_id(part.get("id")) or part.get("id") in seen or not text_value(part.get("pivot")):
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
    elif type(production.get("max_revisions")) is not int or production["max_revisions"] < 0 or not isinstance(production.get("reuse_candidates"), list) or any(not safe_id(v) for v in production["reuse_candidates"]):
        errors.append("invalid revision budget or reuse candidates")
    for key in ("assumptions", "open_questions"):
        if not isinstance(request.get(key), list) or any(not text_value(v) for v in request[key]):
            errors.append(f"{key} must be a text list")
    custom = request.get("additional_checks", [])
    reserved_ids = set(CHECKS) | {key for checks in TASK_CHECKS.values() for key in checks} | {"animation", "target_environment"}
    seen_checks = set()
    if not isinstance(custom, list):
        errors.append("additional_checks must be a list")
    else:
        for check in custom:
            if not isinstance(check, dict) or not safe_id(check.get("id")) or check["id"] in reserved_ids | seen_checks or not isinstance(check.get("area"), str) or check["area"] not in {"art", "technical", "delivery", "target_environment"} or not text_value(check.get("description")):
                errors.append("invalid, duplicate or overriding additional check")
            else:
                seen_checks.add(check["id"])
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
    if not safe_id(aid) or not text_value(brief) or task_type not in TASKS:
        raise ValueError("invalid intake id, brief or task_type")
    if profile is not None and (not isinstance(profile, dict) or not safe_id(profile.get("id")) or not isinstance(profile.get("defaults"), dict) or not isinstance(profile.get("constraints"), list) or any(not text_value(v) for v in profile["constraints"])):
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
    return {
        "mode": "offline_plan_only", "request_id": request["id"], "request_sha256": request_sha256(request),
        "project": request.get("project"), "route": route, "reason": request["production"]["reason"],
        "pending": readiness(request), "reuse_candidates": request["production"]["reuse_candidates"],
        "steps": ["理解需求與交付承諾", "制定設計、參考與可修訂預設", action,
                  "製作與需求指定的後製", "逐項記錄美術／技術／必要目標環境證據", "核對交付檔案並歸檔"],
        "needed_capabilities": {"review_existing": ["library_search"], "reuse": ["asset_inspection", "format_export"], "modify": ["mesh_edit", "format_export"], "generate": ["reference_design", "candidate_generation", "mesh_edit", "format_export"], "split_then_generate": ["part_design", "candidate_generation", "mesh_edit", "format_export"]}[route],
        "required_checks": checks, "paid_submission_authorized_by_this_plan": False,
        "note": "計畫不執行工具、不花費；客戶設定、範例及需求單都不能替代外部操作授權。",
    }


def check_artifact(item: dict, root: Path) -> str | None:
    if not isinstance(item, dict) or not text_value(item.get("path")) or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
        return "artifact requires path and SHA-256"
    try:
        path = evidence_file(item["path"], root)
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            return f"artifact hash mismatch: {item['path']}"
    except (OSError, ValueError) as exc:
        return str(exc)
    return None


def assess(request: dict, evidence: dict, root: Path = ROOT) -> dict:
    checks = required_checks(request)
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    blockers = readiness(request)
    digest = request_sha256(request)
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


def search_library(index: dict, query: str, project: str | None = None) -> list[dict]:
    if not isinstance(index, dict) or index.get("schema_version") != 1 or not isinstance(index.get("entries"), list):
        raise ValueError("invalid library index")
    if project is not None and not safe_id(project):
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
    for name in ("validate", "plan", "assess"):
        command = commands.add_parser(name)
        command.add_argument("request")
        if name == "assess":
            command.add_argument("--evidence", required=True)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--project")
    args = parser.parse_args(argv)
    try:
        if args.command == "intake":
            profile = None
            if args.profile:
                if not safe_id(args.profile):
                    raise ValueError("invalid profile id")
                profile_path = local_path(f"projects/{args.profile}.json")
                if not profile_path.is_relative_to(local_path("projects")):
                    raise ValueError("profile must stay in projects directory")
                profile = read_json(profile_path)
                if not isinstance(profile, dict) or profile.get("schema_version") != 1 or profile.get("id") != args.profile:
                    raise ValueError("profile identity mismatch")
            # 只輸出草稿，協調者以一般檔案工具保存；不默默改寫現有需求。
            result = make_draft(args.id, args.brief, args.type, profile)
        elif args.command == "search":
            result = {"mode": "metadata_search_only", "matches": search_library(read_json(local_path("library/index.json")), args.query, args.project)}
        else:
            request = read_json(local_path(args.request))
            errors = validate_request(request)
            if errors:
                raise ValueError("; ".join(errors))
            if args.command == "validate":
                result = {"status": "valid_request", "request_id": request["id"], "request_sha256": request_sha256(request), "pending": readiness(request), "note": "結構有效不表示已核准製作或驗收通過"}
            elif args.command == "plan":
                result = production_plan(request)
            else:
                result = assess(request, read_json(local_path(args.evidence)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
