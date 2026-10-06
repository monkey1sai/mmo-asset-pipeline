"""Offline demand planning and GLB inventory. Never submits paid work."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity  # noqa: E402
import ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HEAD = re.compile(r"[a-f0-9]{40}\Z")
CATEGORIES = {"character", "creature", "weapon", "building", "environment", "prop"}
DEMANDS = {"source_backed", "inferred", "reuse"}
REQUIRED = {"id", "project", "name", "category", "priority", "demand", "prompt", "target_triangles", "texture_px", "size_m", "pivot", "requires_rig", "postprocess", "sources"}


def positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def validate_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        return ["catalog schema_version must be 1"]
    assets = catalog.get("assets")
    if not isinstance(assets, list) or not assets:
        return ["assets must be a nonempty list"]
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        label = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{label}: must be an object")
            continue
        missing = REQUIRED - asset.keys()
        if missing:
            errors.append(f"{label}: missing {', '.join(sorted(missing))}")
            continue
        aid = asset["id"]
        if not identity.is_asset_id(aid):
            errors.append(f"{label}: unsafe id")
        elif aid in seen:
            errors.append(f"{label}: duplicate id {aid}")
        else:
            seen.add(aid)
        if asset["project"] is not None and not identity.is_asset_id(asset["project"]):
            errors.append(f"{label}: invalid project")
        for field, allowed in (("category", CATEGORIES), ("demand", DEMANDS)):
            if not isinstance(asset[field], str) or asset[field] not in allowed:
                errors.append(f"{label}: invalid {field}")
        if type(asset["priority"]) is not int or asset["priority"] not in (0, 1, 2):
            errors.append(f"{label}: invalid priority")
        for field in ("name", "prompt", "pivot"):
            if not isinstance(asset[field], str) or not asset[field].strip():
                errors.append(f"{label}: {field} must be nonempty text")
        if not positive_int(asset["target_triangles"]):
            errors.append(f"{label}: invalid target_triangles")
        if asset["texture_px"] is not None and not positive_int(asset["texture_px"]):
            errors.append(f"{label}: invalid texture_px")
        size = asset["size_m"]
        if not isinstance(size, list) or len(size) != 3 or any(type(v) not in (int, float) or not 0 < v < float("inf") for v in size):
            errors.append(f"{label}: size_m must have three finite positive dimensions")
        if type(asset["requires_rig"]) is not bool:
            errors.append(f"{label}: requires_rig must be boolean")
        if not isinstance(asset["postprocess"], list) or not asset["postprocess"] or any(not isinstance(v, str) or not v.strip() for v in asset["postprocess"]):
            errors.append(f"{label}: postprocess must list acceptance work")
        sources = asset["sources"]
        if not isinstance(sources, list) or not sources:
            errors.append(f"{label}: missing source evidence")
            continue
        for source in sources:
            if not isinstance(source, dict):
                errors.append(f"{label}: source must be an object")
                continue
            kind = source.get("kind", "repo")
            if kind == "repo":
                if not isinstance(source.get("path"), str) or not source["path"].strip():
                    errors.append(f"{label}: source path missing")
                if not positive_int(source.get("line")) or not isinstance(source.get("head"), str) or not HEAD.fullmatch(source["head"]):
                    errors.append(f"{label}: invalid source line/head")
            elif kind in {"brief", "reference", "library"}:
                if not isinstance(source.get("reference"), str) or not source["reference"].strip():
                    errors.append(f"{label}: {kind} source reference missing")
            else:
                errors.append(f"{label}: unknown source kind")
    return errors


def credit_amount(value: str | float | int) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("credits must be a finite nonnegative number") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("credits must be a finite nonnegative number")
    return amount


def make_plan(catalog: dict, budget: Decimal, cost: Decimal, reserved: set[str], project: str | None = None) -> dict:
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError("; ".join(errors))
    budget = credit_amount(str(budget))
    cost = credit_amount(str(cost))
    if cost == 0:
        raise ValueError("unit cost must be positive")
    projects = {a["project"] or "standalone" for a in catalog["assets"]}
    if project is not None and (not identity.is_asset_id(project) or project not in projects):
        raise ValueError("unknown project filter")
    available = sorted((a for a in catalog["assets"] if a["demand"] != "reuse" and a["id"] not in reserved and (project is None or (a["project"] or "standalone") == project)), key=lambda a: (a["priority"], a["id"]))
    slots = int(budget // cost)
    selected = available[:slots]
    estimate = cost * len(selected)
    return {
        "mode": "offline_plan_only",
        "budget_scope": "subscription_only",
        "budget_credits": str(budget),
        "estimated_unit_cost": str(cost),
        "estimated_cost": str(estimate),
        "unallocated_credits": str(budget - estimate),
        "available_demand_count": len(available),
        "selected_count": len(selected),
        "blocked_or_completed_count": len(reserved),
        "demand_gap": len(available) < slots,
        "note": "估算不是實際扣點或授權；不重複產製既有模型，不因額度剩餘自動追加變體。",
        "assets": [{"id": a["id"], "name": a["name"], "project": a["project"], "priority": a["priority"]} for a in selected],
    }


def inspect_glb(data: bytes) -> dict:
    if len(data) < 20:
        raise ValueError("GLB truncated header")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("GLB invalid magic/version/declared length")
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < length:
        if offset + 8 > length:
            raise ValueError("GLB truncated chunk header")
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        if size % 4 or offset + size > length:
            raise ValueError("GLB invalid chunk length/alignment")
        chunks.append((kind, data[offset:offset + size]))
        offset += size
    if not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError("GLB first chunk must be JSON")
    if sum(kind == 0x4E4F534A for kind, _ in chunks) != 1:
        raise ValueError("GLB requires exactly one JSON chunk")
    doc = json.loads(chunks[0][1].decode("utf-8"))
    if doc.get("asset", {}).get("version") != "2.0":
        raise ValueError("GLB asset.version must be 2.0")
    accessors = doc.get("accessors", [])
    triangles = 0
    primitive_count = 0
    warnings: list[str] = []
    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            primitive_count += 1
            if "POSITION" not in primitive.get("attributes", {}):
                raise ValueError("GLB primitive missing POSITION")
            position_index = primitive["attributes"]["POSITION"]
            if type(position_index) is not int or not 0 <= position_index < len(accessors):
                raise ValueError("GLB invalid POSITION accessor")
            if primitive.get("mode", 4) != 4:
                warnings.append("non-triangle primitive: count not calculated")
                continue
            count_index = primitive.get("indices", position_index)
            if type(count_index) is not int or not 0 <= count_index < len(accessors):
                raise ValueError("GLB invalid count accessor")
            count = accessors[count_index].get("count")
            if not positive_int(count) or count % 3:
                raise ValueError("GLB invalid triangle accessor count")
            triangles += count // 3
    if primitive_count == 0:
        raise ValueError("GLB has no mesh primitives")
    binary = sum(len(payload) for kind, payload in chunks if kind == 0x004E4942)
    for buffer in doc.get("buffers", []):
        if buffer.get("uri"):
            warnings.append("external buffer: dependency must be reviewed locally")
        elif not positive_int(buffer.get("byteLength")) or buffer["byteLength"] > binary:
            raise ValueError("GLB embedded buffer exceeds BIN data")
    for view in doc.get("bufferViews", []):
        index = view.get("buffer")
        buffers = doc.get("buffers", [])
        if type(index) is not int or not 0 <= index < len(buffers):
            raise ValueError("GLB invalid bufferView buffer")
        start, size = view.get("byteOffset", 0), view.get("byteLength")
        if type(start) is not int or start < 0 or not positive_int(size) or start + size > buffers[index]["byteLength"]:
            raise ValueError("GLB bufferView out of bounds")
    external_images = sum(bool(i.get("uri")) and not i["uri"].startswith("data:") for i in doc.get("images", []))
    if external_images:
        warnings.append("external textures: dependency must be reviewed locally")
    if doc.get("extensionsRequired"):
        warnings.append("requires importer extensions: " + ", ".join(doc["extensionsRequired"]))
    return {
        "status": "structural_inventory_only",
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "triangles_per_mesh_copy": triangles,
        "primitives": primitive_count, "meshes": len(doc.get("meshes", [])),
        "nodes": len(doc.get("nodes", [])), "materials": len(doc.get("materials", [])),
        "images": len(doc.get("images", [])), "external_images": external_images,
        "skins": len(doc.get("skins", [])), "animations": len(doc.get("animations", [])),
        "warnings": warnings,
        "not_verified": ["visual_quality", "mesh_topology", "UV_quality", "dimensions_and_pivot", "LOD", "collider", "rig_mapping", "animation", "game_runtime", "unity_import", "license"],
    }


def read_catalog(root: Path) -> dict:
    catalog = identity.read_json(identity.recorded_path(root, "catalog/assets.json"))
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError("; ".join(errors))
    return catalog


def plan_workspace(root: Path, budget: Decimal, cost: Decimal, project: str | None = None) -> dict:
    """以 Operation ledger 決定保留；任何阻擋紀錄使整份離線計畫停止，不產生部分結果。"""
    catalog = read_catalog(root)
    entries = ledger.load(root)
    blocking = entries.blocking()
    if blocking:
        raise ValueError("operation ledger blocks planning: " + ", ".join(f"{op.operation_id}={op.problem or op.state}" for op in blocking))
    return make_plan(catalog, budget, cost, entries.reserved_catalog_assets(), project)


def validate_workspace(root: Path) -> list[str]:
    """交叉核對需求與帳本的 catalog 連結，以及匯入紀錄的證據雜湊。"""
    known = {asset["id"] for asset in read_catalog(root)["assets"]}
    issues = []
    for path in sorted((root / "requests").rglob("*.json")):
        request = identity.read_json(path)
        link = request.get("catalog_asset_id")
        if link is not None and link not in known:
            issues.append(f"request {request.get('id')}: catalog_asset_id not in catalog: {link}")
    entries = ledger.load(root)
    for op in entries.operations:
        if op.catalog_asset_id is not None and op.catalog_asset_id not in known:
            issues.append(f"operation {op.operation_id}: catalog_asset_id not in catalog: {op.catalog_asset_id}")
    issues.extend(f"operation {op.operation_id}: {op.problem}" for op in entries.blocking() if op.problem)
    return issues + entries.verify_evidence()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="離線模型需求規劃與 GLB 清點（不扣點、不連網）")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    plan = commands.add_parser("plan")
    plan.add_argument("--budget", required=True)
    plan.add_argument("--unit-cost", default="0.5")
    plan.add_argument("--project", help="清單中的客戶 ID；獨立需求用 standalone")
    brief = commands.add_parser("brief")
    brief.add_argument("asset_id")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("path")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_glb(identity.command_path(ROOT, args.path).read_bytes())
        else:
            catalog = read_catalog(ROOT)
            if args.command == "validate":
                issues = validate_workspace(ROOT)
                if issues:
                    raise ValueError("; ".join(issues))
                result = {"status": "valid", "assets": len(catalog["assets"]), "projects": dict(Counter(a["project"] or "standalone" for a in catalog["assets"])),
                          "operations": len(ledger.load(ROOT).operations), "note": "schema, catalog links and ledger evidence verified; source freshness and runtime not checked"}
            elif args.command == "plan":
                result = plan_workspace(ROOT, credit_amount(args.budget), credit_amount(args.unit_cost), args.project)
            else:
                result = next((a for a in catalog["assets"] if a["id"] == args.asset_id), None)
                if result is None:
                    raise ValueError("unknown asset id")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
