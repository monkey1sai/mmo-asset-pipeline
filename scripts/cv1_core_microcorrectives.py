"""Pose-driven micro-correctives for single core triangles that fold flat in a contract pose.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_core_microcorrectives.py -- \
       --contract <joint-range-contract.json> --rules-in <rules.json> --sites <sites.json> --tag <name> --out-dir <assets dir>
Each site names a rest-space triangle centroid, the contract motion and level where it folds, and the bone that
drives the fix. The triangle's apex is moved away from its longest edge, in the posed state, until the triangle
has the requested share of its rest area; the offset is stored in rest space as a one-vertex shape key driven by
that bone reaching the pose. Weights and Basis are not touched, so other poses see at most a fraction of a
sub-millimetre offset. The input BLEND is not modified; a new BLEND and rules file are written.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math

parser = argparse.ArgumentParser()
parser.add_argument("--contract", required=True)
parser.add_argument("--rules-in", required=True)
parser.add_argument("--sites", required=True)
parser.add_argument("--tag", required=True)
parser.add_argument("--out-dir", required=True)
parser.add_argument("--area-ratio", type=float, default=0.08)
parser.add_argument("--poses")
parser.add_argument("--account-existing", action="store_true", help="compute each offset on top of the correctives already active at the site pose; skip sites already above target")
parser.add_argument("--off-at-frozen-levels", action="store_true", help="hat curve that is zero at the typical and extreme levels of the site motion, so frozen-level results do not change")
parser.add_argument("--first-number", type=int, default=1, help="number of the first new site, so keys and drivers do not collide with earlier fold fixes in the same BLEND")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")
out_dir.mkdir(parents=True)
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules_in).read_text(encoding="utf-8"))
sites = json.loads((ROOT / args.sites).read_text(encoding="utf-8"))
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8")) if args.poses else {}
motions = {m["id"]: m for m in contract["motions"]}
AXES = {name: Vector(value) for name, value in contract["axes"].items()}
BODY = {"forward": AXES["forward"], "back": -AXES["forward"], "up": AXES["up"], "down": -AXES["up"], "left": AXES["left"], "right": -AXES["left"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
core = bpy.data.objects["SM_RO_core"]
if core.data.shape_keys is None:
    core.shape_key_add(name="Basis", from_mix=False)
group_names = [g.name for g in core.vertex_groups]
basis = [v.co.copy() for v in core.data.vertices]
core.data.calc_loop_triangles()
triangles = [(tuple(t.vertices), t.center.copy()) for t in core.data.loop_triangles]


def direction(name, side):
    if name in ("out", "in"):
        lateral = AXES["left"] if side == "L" else -AXES["left"]
        return lateral if name == "out" else -lateral
    return BODY.get(name)


def reset():
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)


def set_motion(motion_id, level):
    """Body steps of a contract motion; steps that need the hand frame are skipped (they do not move the core sites)."""
    motion = motions[motion_id]
    reset()
    if motion.get("requires_pose"):
        for name, quaternion in poses[motion["requires_pose"]].items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
    for step in motion["steps"]:
        side = step.get("side", motion.get("side"))
        bone = bones[step["bone"]]
        if step["kind"] == "swing":
            toward = direction(step["toward"], side)
            if toward is None:
                continue
            axis = (bone.tail_local - bone.head_local).normalized().cross(toward)
        else:
            axis = (bones[step["about_bone"]].tail_local - bones[step["about_bone"]].head_local) if "about_bone" in step else direction(step["about"], side)
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(bone.matrix_local.to_3x3().inverted() @ axis.normalized(), math.radians(step["degrees"]) * level)
    bpy.context.view_layer.update()


def pose_rel(name):
    pb = arm.pose.bones[name]
    rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
    local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
    return (rest_local.inverted() @ local).to_quaternion()


def skin_matrix(index):
    blended = Matrix(((0,) * 4,) * 4)
    for g in core.data.vertices[index].groups:
        name = group_names[g.group]
        if g.weight > 0 and name in bones:
            blended += (arm.pose.bones[name].matrix @ bones[name].matrix_local.inverted()) * g.weight
    return blended


clip_actions = {}


def pose_from_clip(spec):
    """Pose the armature from a clip action at a (possibly fractional) frame; actions are appended once."""
    key = (spec["clip_blend"], spec["action"])
    if key not in clip_actions:
        with bpy.data.libraries.load(str(ROOT / spec["clip_blend"]), link=False) as (src, dst):
            dst.actions = [spec["action"]]
        clip_actions[key] = bpy.data.actions[spec["action"]]
    reset()
    arm.animation_data_create()
    arm.animation_data.action = clip_actions[key]
    frame = math.floor(spec["frame"])
    bpy.context.scene.frame_set(frame, subframe=spec["frame"] - frame)
    bpy.context.view_layer.update()


def release_clip():
    if arm.animation_data:
        arm.animation_data.action = None
    reset()
    bpy.context.view_layer.update()


def frozen_driver_maximum(bones, targets):
    """Largest driver value (product of rotation-difference progress) over every frozen-level contract pose."""
    best, where = 0.0, None
    for motion_id in motions:
        for name in ("typical", "extreme"):
            set_motion(motion_id, contract["levels"][name])
            value = 1.0
            for bone, target_q in zip(bones, targets):
                value *= rules_math.rotation_difference_progress(tuple(pose_rel(bone)), tuple(target_q))
            if value > best:
                best, where = value, f"{motion_id}@{name}"
    return best, where


report = []
for number, site in enumerate(sites["sites"], args.first_number):
    centre = Vector(site["centre"])
    corners, found = min(triangles, key=lambda t: (t[1] - centre).length)
    if (found - centre).length > 0.003:
        raise SystemExit(f"SITE_TRIANGLE_NOT_FOUND {site}")
    from_clip = "pose_from" in site
    driver_bones = site.get("driver_bones", [site.get("driver_bone")])
    if from_clip:
        level = None
        pose_from_clip(site["pose_from"])
        site.setdefault("motion", f"clip:{site['pose_from']['action']}@{site['pose_from']['frame']}")
        site.setdefault("level", "clip")
        site.setdefault("driver_bone", "*".join(driver_bones))
    else:
        level = contract["levels"][site["level"]]
        set_motion(site["motion"], level)
    targets = [pose_rel(b) for b in driver_bones]
    target = targets[0]
    for bone, target_q in zip(driver_bones, targets):
        if 2 * math.acos(min(1.0, abs(target_q.w))) < math.radians(5):
            raise SystemExit(f"DRIVER_BONE_BARELY_MOVES {bone} {site}")
    matrices = {i: skin_matrix(i) for i in corners}
    existing = {i: Vector() for i in corners}
    if args.account_existing:
        # Correctives already in the rules, evaluated at this pose, move the corners before the new offset is sought.
        full_pose = {pb.name: tuple(pose_rel(pb.name)) for pb in arm.pose.bones}
        source_state = site.get("state", {}) if from_clip else motions[site["motion"]].get("state", {})
        state = {d["key"]: float(source_state.get(d["key"], 0.0)) for d in rules["drivers"].values() if d["type"] == "state"}
        for (mesh_name, key_name), weight in rules_math.evaluate(rules, full_pose, state).items():
            if mesh_name == core.name and weight:
                block = core.data.shape_keys.key_blocks[key_name]
                for i in corners:
                    existing[i] += (block.data[i].co - basis[i]) * weight
    posed = {i: matrices[i] @ (basis[i] + existing[i]) for i in corners}
    rest_area = (basis[corners[1]] - basis[corners[0]]).cross(basis[corners[2]] - basis[corners[0]]).length / 2
    area = lambda: (posed[corners[1]] - posed[corners[0]]).cross(posed[corners[2]] - posed[corners[0]]).length / 2
    before = area() / rest_area
    base = list(max(((corners[i], corners[j]) for i in range(3) for j in range(i + 1, 3)), key=lambda e: (posed[e[0]] - posed[e[1]]).length))
    apex = next(v for v in corners if v not in base)
    if "move_corner" in site:
        apex = corners[site["move_corner"]]
        base = [v for v in corners if v != apex]
    goal = site.get("area_ratio", args.area_ratio)
    if args.account_existing and before >= goal:
        report.append({"site": number, "motion": site["motion"], "level": site["level"], "driver_bone": site["driver_bone"], "triangle_vertices": list(corners),
                       "skipped": "already above the target with the existing correctives", "area_ratio_with_existing": round(before, 4)})
        if from_clip:
            release_clip()
        continue
    start = posed[apex].copy()
    for _ in range(400):
        if area() / rest_area >= goal:
            break
        edge = (posed[base[1]] - posed[base[0]]).normalized()
        offset = posed[apex] - posed[base[0]]
        away = offset - edge * offset.dot(edge)
        if away.length < 1e-7:
            rest_edge = (basis[base[1]] - basis[base[0]]).normalized()
            rest_offset = basis[apex] - basis[base[0]]
            away = matrices[apex].to_3x3() @ (rest_offset - rest_edge * rest_offset.dot(rest_edge))
        posed[apex] += away.normalized() * 0.00005
    moved = posed[apex] - start
    linear = matrices[apex].to_3x3()
    if float(np.linalg.cond(np.array(linear))) > 20:
        raise SystemExit(f"UNSTABLE_INVERSE_SKIN site {number}")
    if f"SKC_core_fold_{number:02d}" in core.data.shape_keys.key_blocks or f"fold.{number:02d}" in rules["drivers"]:
        raise SystemExit(f"SITE_NUMBER_TAKEN {number}")
    key = core.shape_key_add(name=f"SKC_core_fold_{number:02d}", from_mix=False)
    key.data[apex].co = basis[apex] + linear.inverted() @ moved
    driver = f"fold.{number:02d}"
    if len(driver_bones) == 1:
        rules["drivers"][driver] = {"type": "rotation_difference", "bone": driver_bones[0], "target_quaternion_wxyz": list(target),
                                    "target_source": f"{driver_bones[0]} in {site['motion']} at the {site['level']} level"}
    else:
        # Product driver: active only when every bone is near its pose at the site (e.g. hip and knee together).
        parts = []
        for k, (bone, target_q) in enumerate(zip(driver_bones, targets)):
            part = f"{driver}.{k}"
            rules["drivers"][part] = {"type": "rotation_difference", "bone": bone, "target_quaternion_wxyz": list(target_q),
                                      "target_source": f"{bone} in {site['motion']}"}
            parts.append(part)
        rules["drivers"][driver] = {"type": "product", "of": parts}
    curve = {"type": "linear"}
    if from_clip or site.get("off_at_all_frozen_poses"):
        # Zero at every frozen-level contract pose, so the frozen sweep cannot change; the hat starts above the largest value.
        frozen_max, frozen_where = frozen_driver_maximum(driver_bones, targets)
        # min_prev narrows the hat around the site pose, so a fix for one clip does not act in unrelated poses of another.
        start = max(frozen_max + 0.02, float(site.get("min_prev", 0.0)))
        if start >= 0.97:
            raise SystemExit(f"SITE_ACTIVE_AT_A_FROZEN_POSE {number} {frozen_max:.3f} at {frozen_where}")
        curve = {"type": "hat", "prev": round(start, 4), "at": 1.0, "frozen_pose_maximum": round(frozen_max, 4), "frozen_pose_maximum_at": frozen_where}
        if from_clip:
            release_clip()
    elif args.off_at_frozen_levels:
        # Progress of the driver bone at the motion's frozen levels; the hat starts just above the largest of them.
        frozen = []
        for name in ("typical", "extreme"):
            set_motion(site["motion"], contract["levels"][name])
            frozen.append(rules_math.rotation_difference_progress(tuple(pose_rel(site["driver_bone"])), tuple(target)))
        start = max(frozen) + 0.02
        if start >= 0.97:
            raise SystemExit(f"SITE_TOO_CLOSE_TO_A_FROZEN_LEVEL {number} {frozen}")
        curve = {"type": "hat", "prev": round(start, 4), "at": 1.0, "frozen_level_progress": [round(v, 4) for v in frozen]}
        set_motion(site["motion"], level)
    rules["channels"].append({"mesh": core.name, "morph": key.name, "owner": "runtime_evaluator", "kind": "body_pose", "driver": driver,
                              "curve": {k: v for k, v in curve.items() if k in ("type", "prev", "at", "next")}})
    report.append({"site": number, "motion": site["motion"], "level": site["level"], "driver_bone": site["driver_bone"], "triangle_vertices": list(corners), "apex": apex,
                   "area_ratio_before": round(before, 4), "area_ratio_after": round(area() / rest_area, 4), "posed_offset_mm": round(moved.length * 1e3, 3),
                   "existing_correctives_counted": args.account_existing, "curve": curve})
reset()
bpy.context.view_layer.update()
rules["id"] = f"ro-swordsman-character-v1-v001-{args.tag}"
rules_math.validate_rules(rules)
(out_dir / "corrective-rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
blend_path = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "source": source, "source_sha256_after": sha(ROOT / source["path"]),
           "output": {"path": blend_path.relative_to(ROOT).as_posix(), "sha256": sha(blend_path)}, "area_ratio_target": args.area_ratio, "sites": report,
           "scope": "One vertex per site, moved only as far as the triangle needs to keep a share of its rest area in that pose. Not a shoulder or hip deformation fix."}
(out_dir / "core-microcorrectives-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_CORE_MICRO", json.dumps(report))
