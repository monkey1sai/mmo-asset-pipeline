"""Offline asset planning. No network, credentials, or provider submissions."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def local_path(value, root=ROOT):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path must stay inside this repository")
    return path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(data, output, ensure_ascii=False, indent=2)
        output.write("\n")


def check_brief(brief, config=None, rigs=None):
    config = config or load_json(ROOT / "configs/pipeline.json")
    rigs = rigs or load_json(ROOT / "configs/rig_profiles.json")
    if not isinstance(brief, dict):
        return ["Brief must be an object"]
    errors = []
    for key in ("asset_id", "asset_type", "engine", "delivery_mode", "description", "style", "budget_profile"):
        if not isinstance(brief.get(key), str) or not brief[key].strip():
            errors.append(f"{key}: required non-empty string")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", brief.get("asset_id", "") if isinstance(brief.get("asset_id"), str) else ""):
        errors.append("asset_id: use lowercase letters, numbers and hyphens")
    if brief.get("asset_type") not in config["asset_types"]:
        errors.append("asset_type: unsupported")
    if brief.get("engine") != config["engine"]:
        errors.append("engine: this contract targets Unity")
    if brief.get("delivery_mode") not in config["delivery_modes"]:
        errors.append("delivery_mode: unsupported")
    scale = brief.get("scale_meters")
    if type(scale) not in (int, float) or not 0 < scale < float("inf"):
        errors.append("scale_meters: must be finite and positive")
    if not isinstance(brief.get("budget_profile"), str) or brief["budget_profile"] not in config["profiles"]:
        errors.append("budget_profile: unknown; add a versioned profile first")
    if brief.get("asset_type") in ("character", "outfit"):
        if not isinstance(brief.get("rig_profile"), str) or brief["rig_profile"] not in rigs:
            errors.append("rig_profile: unknown; add a rig family/variant first")
        if not isinstance(brief.get("body_variant"), str) or not brief["body_variant"].strip():
            errors.append("body_variant: required for clothing compatibility")
        actions = brief.get("required_actions")
        if not isinstance(actions, list) or not actions or any(not isinstance(a, str) or not a.strip() for a in actions):
            errors.append("required_actions: non-empty action list required")
    parts = brief.get("parts", [])
    if not isinstance(parts, list):
        errors.append("parts: must be a list")
        parts = []
    ids = set()
    for part in parts:
        if not isinstance(part, dict):
            errors.append("part: must be an object")
            continue
        part_id = part.get("id")
        if not isinstance(part_id, str) or not part_id.strip():
            errors.append("part.id: required string")
        elif part_id in ids:
            errors.append(f"part.id: duplicate {part_id}")
        else:
            ids.add(part_id)
        if not isinstance(part.get("slot"), str) or not part["slot"].strip():
            errors.append("part.slot: required string")
        mode = part.get("deformation")
        if mode not in ("skin", "rigid", "secondary"):
            errors.append("part.deformation: use skin, rigid or secondary")
        if mode == "rigid":
            rig_id = brief.get("rig_profile")
            bones = rigs.get(rig_id, {}).get("bones", {}) if isinstance(rig_id, str) else {}
            if not isinstance(part.get("parent_bone"), str) or part["parent_bone"] not in bones:
                errors.append("rigid part: valid parent_bone required")
        if mode == "secondary" and part.get("motion_solution") not in ("secondary-bones", "unity-cloth", "baked-animation"):
            errors.append("secondary part: choose secondary-bones, unity-cloth or baked-animation")
    variants = brief.get("variants", [])
    if not isinstance(variants, list):
        errors.append("variants: must be a list")
    else:
        for variant in variants:
            if not isinstance(variant, dict) or not all(isinstance(variant.get(k), str) and variant[k].strip() for k in ("id", "reason")) or not isinstance(variant.get("impacts"), list) or not variant["impacts"]:
                errors.append("variant: id, reason and non-empty impacts required")
    if brief.get("delivery_mode") == "production":
        refs = brief.get("references", {})
        if not isinstance(refs, dict):
            refs = {}
        views = refs.get("orthographic_views", [])
        if not isinstance(views, list) or not {"front", "back", "side"}.issubset(v.get("view") for v in views if isinstance(v, dict) and isinstance(v.get("view"), str) and isinstance(v.get("path"), str) and v["path"].strip()):
            errors.append("production: front/back/side reference entries required")
        for key in ("part_boundaries", "clearance_notes"):
            if not isinstance(refs.get(key), str) or refs[key].strip().lower() in ("", "pending", "unknown"):
                errors.append(f"production: resolved {key} required")
    return errors


def make_plan(brief):
    errors = check_brief(brief)
    if errors:
        raise ValueError("; ".join(errors))
    kind = brief["asset_type"]
    character = kind in ("character", "outfit")
    skills = ["blender-director"]
    if character:
        skills.append("character-artist")
    elif kind != "weapon":
        skills.append("environment-artist")
    stages = ["concept-exploration", "orthographic-and-part-design", "source-selection", "blender-refinement", "unity-preview", "retopology", "uv-and-materials"]
    if character:
        skills += ["retopology", "rigging", "animation"]
        stages += ["rig-family-and-part-deformation", "deformation-and-outfit-matrix"]
    elif kind == "weapon":
        stages += ["grip-sockets-and-rigid-animation"]
    else:
        stages += ["modular-and-accent-assembly", "lod-and-collision"]
    skills += ["asset-optimization", "export-pipeline", "unity-export"]
    stages += ["blender-technical-check", "unity-import-and-runtime", "visual-and-performance-evidence", "versioned-delivery"]
    return {
        "contract_version": load_json(ROOT / "configs/pipeline.json")["contract_version"],
        "asset_id": brief["asset_id"], "delivery_mode": brief["delivery_mode"],
        "status": "PLANNED", "production_status": "UNVERIFIED", "network_calls": 0,
        "brief_sha256": hashlib.sha256(json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "stages": [{"name": s, "status": "NOT_STARTED"} for s in stages],
        "skill_paths": [f"vendor/blender-skills/skills/{s}/SKILL.md" for s in skills],
        "deliverables": ["versioned-source.blend", "Unity-FBX-and-textures", "part-and-material-manifest", "technical-report", "Unity-prefab-and-runtime-evidence"],
        "gaps": ["Model files not produced", "Blender deformation and visual checks not run", "Unity runtime not tested", "Target hardware/render pipeline not locked"],
    }


def verify_vendor(root=ROOT):
    lock = load_json(root / "vendor/blender-skills/source-lock.json")
    errors = []
    base = root / "vendor/blender-skills"
    expected = set(lock["files"])
    actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file() and p.relative_to(base).as_posix() != "source-lock.json"}
    for extra in sorted(actual - expected):
        errors.append(f"unlocked file: {extra}")
    for name, digest in lock["files"].items():
        path = local_path(name, base)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"missing or changed: {name}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check-brief", "plan"):
        command = commands.add_parser(name)
        command.add_argument("brief")
        if name == "plan":
            command.add_argument("--out", required=True)
    commands.add_parser("verify-vendor")
    args = parser.parse_args()
    try:
        if args.command == "verify-vendor":
            errors = verify_vendor()
        else:
            brief = load_json(local_path(args.brief))
            errors = check_brief(brief)
            if not errors and args.command == "plan":
                write_new(local_path(args.out), make_plan(brief))
        if errors:
            print("FAIL: " + "; ".join(errors))
            return 1
        print("PASS: offline " + args.command + " (does not certify a production asset)")
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
