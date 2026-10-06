"""Character V1 joint-range sweep: pose each supported joint at typical and extreme levels and measure the evaluated mesh.

Run: blender -b --factory-startup --disable-autoexec <character.blend> --python scripts/cv1_joint_range.py -- \
       --contract <joint-range-contract.json> --out <new dir> (--rules <rules.json> | --no-rules)
       [--request <request.json>] [--poses <poses.json>] [--no-render]
The BLEND is never saved and an existing output folder is refused. Directions are anatomical and resolved from the
rest skeleton, so the same contract applies to every candidate that keeps the contract's bone names.

All skinned meshes except the contract's excluded ones are measured as one triangle soup, so penetration between
meshes counts. Triangles driven by hand bones form the hand region whatever mesh they live in.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math
from cv1_soup import Soup

parser = argparse.ArgumentParser()
parser.add_argument("--contract", required=True)
parser.add_argument("--out", required=True)
rule_choice = parser.add_mutually_exclusive_group(required=True)
rule_choice.add_argument("--rules")
rule_choice.add_argument("--no-rules", action="store_true")
parser.add_argument("--request")
parser.add_argument("--poses")
parser.add_argument("--no-render", action="store_true")
parser.add_argument("--only", help="comma-separated motion ids; diagnostic run, never a gate pass")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


contract_path = (ROOT / args.contract).resolve()
contract = json.loads(contract_path.read_text(encoding="utf-8"))
bound = None
if args.request:
    request = json.loads((ROOT / args.request).read_text(encoding="utf-8"))
    bound = request["support_envelope"]["joint_range_contract"]["sha256"] == sha(contract_path)
    if not bound:
        raise SystemExit("CONTRACT_NOT_BOUND_TO_REQUEST")
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8")) if args.rules else None
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8")) if args.poses else {}
if args.request:
    # Arm rotations the request froze for a candidate-supplied pose must be used exactly; the body ceilings were measured with them.
    for pose_name, frozen in request["support_envelope"].get("frozen_poses", {}).items():
        for bone_name, quaternion in frozen["arm_rotations"].items():
            given = poses.get(pose_name, {}).get(bone_name)
            if pose_name in poses and (given is None or max(abs(a - b) for a, b in zip(given, quaternion)) > 1e-9):
                raise SystemExit(f"FROZEN_POSE_MISMATCH {pose_name} {bone_name}")
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
out.mkdir(parents=True)

scene = bpy.context.scene
armatures = [o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children)]
assert len(armatures) == 1, [o.name for o in armatures]
arm = armatures[0]
# Skinned means parented to the armature or deformed by it through a modifier, wherever the object sits.
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))),
                 key=lambda o: o.name)
excluded = set(contract["limits"]["excluded_meshes"])
meshes = [o for o in skinned if o.name not in excluded]
if arm.animation_data:
    arm.animation_data.action = None
for obj in skinned:
    keys = obj.data.shape_keys
    if keys:
        keys.animation_data_clear()
        for key in keys.key_blocks[1:]:
            key.value = 0.0
bones = arm.data.bones
AXES = {name: Vector(value) for name, value in contract["axes"].items()}
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
limits = contract["limits"]


def reset_pose():
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)


def bone_dir(name):
    return (bones[name].tail_local - bones[name].head_local).normalized()


def hand_frame(side):
    """Palmar and radial directions from rest landmarks; index is the outer finger nearest the thumb."""
    names = contract["hand_landmarks"]
    mcp = {i: bones[names["finger_base"].format(i=i, side=side)].head_local for i in (1, 2, 3, 4)}
    wrist = bones[names["hand"].format(side=side)].head_local
    thumb = bones[names["thumb_base"].format(side=side)].head_local
    index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
    along = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
    across = mcp[index] - mcp[pinky]
    radial = (across - along * across.dot(along)).normalized()
    palmar = radial.cross(along) if side == "R" else along.cross(radial)
    return {"palmar": palmar.normalized(), "dorsal": -palmar.normalized(), "radial": radial, "ulnar": -radial, "index_finger": index}


HAND_DIRECTIONS = ("palmar", "dorsal", "radial", "ulnar")
HANDS = {side: hand_frame(side) for side in ("L", "R") if contract["hand_landmarks"]["hand"].format(side=side) in bones
         and contract["hand_landmarks"]["thumb_base"].format(side=side) in bones
         and all(contract["hand_landmarks"]["finger_base"].format(i=i, side=side) in bones for i in (1, 2, 3, 4))}


def direction(name, side):
    if name in ("out", "in"):
        lateral = AXES["left"] if side == "L" else -AXES["left"]
        return lateral if name == "out" else -lateral
    if name in ("forward", "back"):
        return AXES["forward"] if name == "forward" else -AXES["forward"]
    if name in ("up", "down"):
        return AXES["up"] if name == "up" else -AXES["up"]
    if name in ("left", "right"):
        return AXES["left"] if name == "left" else -AXES["left"]
    return HANDS[side][name]


def step_rotation(step, side, level):
    """Rest-frame local quaternion for one step; swing rotates the bone toward a direction, twist about an axis."""
    bone = bones[step["bone"]]
    angle = math.radians(step["degrees"]) * level
    if step["kind"] == "swing":
        axis = bone_dir(step["bone"]).cross(direction(step["toward"], side))
    else:
        axis = bone_dir(step["about_bone"]) if "about_bone" in step else direction(step["about"], side)
    if axis.length < 1e-6:
        raise SystemExit(f"DEGENERATE_AXIS {step}")
    return Quaternion(bone.matrix_local.to_3x3().inverted() @ axis.normalized(), angle)


def apply(motion, level):
    reset_pose()
    for name, quaternion in poses.get(motion.get("requires_pose"), {}).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
    for step in motion["steps"]:
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ step_rotation(step, step.get("side", motion.get("side")), level)
    bpy.context.view_layer.update()
    if rules:
        pose = {}
        for pb in arm.pose.bones:
            rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
            local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
            pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
        # Helper bones (pauldrons, coat panels) follow their sources before the morph rules read the pose.
        for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
            pose[name] = quaternion
        bpy.context.view_layer.update()
        state = {d["key"]: motion.get("state", {}).get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
        for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
            bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
        bpy.context.view_layer.update()


# ---- soup: one vertex/triangle/edge list over all measured meshes (scripts/cv1_soup.py, shared with the clip check) ----
soup = Soup(meshes, limits)
reset_pose()
bpy.context.view_layer.update()
soup.set_rest()
evaluated_points, measure = soup.evaluated_points, soup.measure
tris, tri_hand, tri_armour, bone_vertices, rest = soup.tris, soup.tri_hand, soup.tri_armour, soup.bone_vertices, soup.rest
armour_meshes, armour_bones, armour_slack = soup.armour_meshes, soup.armour_bones, soup.armour_slack
rest_hand_self, rest_hand_other, rest_other, rest_armour, rest_depth = soup.rest_hand_self, soup.rest_hand_other, soup.rest_other, soup.rest_armour, soup.rest_depth

# ---- render setup: gray workbench, orthographic, one fixed camera per motion ----
camera_data = bpy.data.cameras.new("CV1_JointRangeCamera")
camera = bpy.data.objects.new("CV1_JointRangeCamera", camera_data)
scene.collection.objects.link(camera)
camera_data.type = "ORTHO"
camera_data.clip_start, camera_data.clip_end = 0.05, 20.0
scene.camera = camera
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.62, 0.62, 0.62)
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = contract["render"]["tile_px"]
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj not in skinned:
        obj.hide_render = True


def aim(motion):
    side = motion.get("side")
    focus = sum((bones[name].head_local for name in motion["focus_bones"]), Vector()) / len(motion["focus_bones"])
    view = Vector()
    for name, weight in motion["view"].items():
        view += direction(name, side) * weight
    view.normalize()
    camera_data.ortho_scale = motion["ortho_scale"]
    camera.location = arm.matrix_world @ focus + view * 4.0
    camera.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    return {"focus": [round(c, 4) for c in focus], "view": [round(c, 4) for c in view], "ortho_scale": motion["ortho_scale"]}


def render(name):
    if args.no_render:
        return None
    target = out / "tiles" / f"{name}.png"
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    return target.relative_to(ROOT).as_posix()


ceilings = limits.get("ceilings")
guard_low, guard_high = limits["hand_edge_ratio"]


def guarded(level_row):
    ratio = level_row["hand_edge_ratio"]
    return ratio is None or (ratio[0] >= guard_low and ratio[1] <= guard_high)


results, neutral_tiles = [], {}
only = set(args.only.split(",")) if args.only else None
for motion in contract["motions"]:
    if only is not None and motion["id"] not in only:
        continue
    side = motion.get("side")
    named = {s["bone"] for s in motion["steps"]} | {s["about_bone"] for s in motion["steps"] if "about_bone" in s} | set(motion["focus_bones"])
    missing = sorted(named - set(bones.keys()))
    uses_hand = any(s.get("toward") in HAND_DIRECTIONS for s in motion["steps"]) or any(k in HAND_DIRECTIONS for k in motion["view"])
    hand_sides = {s.get("side", side) for s in motion["steps"]} if uses_hand else set()
    if missing or not hand_sides <= set(HANDS):
        results.append({"id": motion["id"], "region": motion["region"], "status": "missing_bones", "missing": missing or ["hand landmarks"], "pass": False})
        continue
    if motion.get("requires_pose") and motion["requires_pose"] not in poses:
        results.append({"id": motion["id"], "region": motion["region"], "status": "missing_pose", "missing": [motion["requires_pose"]], "pass": False})
        continue
    row = {"id": motion["id"], "region": motion["region"], "status": "measured", "camera": aim(motion), "levels": {}}
    camera_key = json.dumps(row["camera"], sort_keys=True)
    if camera_key not in neutral_tiles:
        reset_pose()
        bpy.context.view_layer.update()
        neutral_tiles[camera_key] = render(f"{motion['id']}--neutral")
    row["neutral_tile"] = neutral_tiles[camera_key]
    for level_name, level in contract["levels"].items():
        apply(motion, level)
        points = evaluated_points()
        smoke = None
        if "expect" in motion:
            pb = arm.pose.bones[motion["expect"]["bone"]]
            smoke = (pb.tail - bones[pb.name].tail_local).dot(direction(motion["expect"]["toward"], motion["expect"].get("side", side)))
        # Every stepped bone must actually carry and move skin; a bone without weights would otherwise pass untouched.
        idle = sorted(bone for bone in {s["bone"] for s in motion["steps"]}
                      if len(bone_vertices.get(bone, ())) < 3 or max((points[i] - rest[i]).length for i in bone_vertices[bone]) < limits["deform_min_displacement_m"])
        row["levels"][level_name] = {"level": level, "direction_smoke_m": smoke, "bones_not_deforming": idle, **measure(points), "tile": render(f"{motion['id']}--{level_name}")}
    typical, extreme = row["levels"]["typical"], row["levels"]["extreme"]
    hand_levels = [typical, extreme] if motion["gate_extreme_hand_region"] else [typical]
    # Pose-induced penetration away from the hands may not exceed what the baseline shows for the same motion.
    # A motion the baseline could not pose gets no allowance: zero new pairs and the hand guard's stretch bound.
    default = {level: {"other_new_pairs": 0, "max_other_edge_ratio": guard_high} for level in ("typical", "extreme")}
    limit = None if ceilings is None else ceilings.get(motion["id"], default)
    row["gate"] = {
        # Direction is judged at the typical level only: past 90 degrees a correct swing can lose its initial component.
        "direction": typical["direction_smoke_m"] is None or typical["direction_smoke_m"] > 0,
        "deforms": not typical["bones_not_deforming"],
        "no_collapse": typical["collapsed_triangles"] == 0 and extreme["collapsed_triangles"] == 0,
        "hand_self_intersection_zero": all(r["hand_self_pairs"] == 0 for r in hand_levels),
        "hand_other_new_intersection_zero": all(r["hand_other_new_pairs"] == 0 for r in hand_levels),
        "hand_shape_guard": guarded(typical) and guarded(extreme),
        # Without recorded ceilings (calibration run) the ratchet cannot be judged and the motion does not pass.
        "other_intersections_within_ceiling": bool(limit) and all(row["levels"][n]["other_new_pairs"] <= limit[n]["other_new_pairs"] for n in ("typical", "extreme")),
        "other_stretch_within_ceiling": bool(limit) and extreme["other_edge_ratio"][1] <= limit["extreme"]["max_other_edge_ratio"] * (1 + 1e-6),
    }
    # The armour depth gate exists only when the contract names armour meshes; otherwise nothing was measured.
    if armour_meshes:
        row["gate"]["armor_contact_depth"] = all(row["levels"][n]["armor_depth_violations"] == 0 for n in ("typical", "extreme"))
    row["pass"] = all(row["gate"].values())
    results.append(row)
reset_pose()
# Overlap that exists before any pose: none inside the hands, and no more away from the hands than the baseline has.
rest_gate = {"hand_self_intersection_zero": len(rest_hand_self) == 0,
             "other_pairs_within_ceiling": "rest_other_pairs_ceiling" in limits and len(rest_other) <= limits["rest_other_pairs_ceiling"]}

summary = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string,
    "subject": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
    "contract": {"path": contract_path.relative_to(ROOT).as_posix(), "sha256": sha(contract_path), "bound_to_request": bound},
    "rules": {"path": args.rules, "sha256": sha(ROOT / args.rules)} if args.rules else "explicitly none (--no-rules): pure skinning, all shape keys at 0",
    "poses": {"path": args.poses, "sha256": sha(ROOT / args.poses)} if args.poses else None,
    "armor_contact": {"meshes": sorted(armour_meshes), "bones": sorted(armour_bones), "slack_m": armour_slack, "rest_pairs": len(rest_armour),
                      "rest_depth_max_m": max(rest_depth.values(), default=0.0), "triangles": sum(tri_armour)},
    "armature": arm.name, "bones": len(bones), "measured_meshes": [o.name for o in meshes], "excluded_meshes": sorted(excluded & {o.name for o in skinned}),
    "soup": {"vertices": len(rest), "triangles": len(tris), "hand_region_triangles": sum(tri_hand)},
    "rest_pairs": {"hand_self": len(rest_hand_self), "hand_other": len(rest_hand_other), "other": len(rest_other)},
    "rest_gate": rest_gate,
    "hand_frames": {side: {k: ([round(c, 4) for c in v] if isinstance(v, Vector) else v) for k, v in frame.items()} for side, frame in HANDS.items()},
    "calibration_run": ceilings is None, "partial_run": sorted(only) if only is not None else None,
    "motions": len(results), "measured": sum(1 for r in results if r["status"] == "measured"), "missing": sum(1 for r in results if r["status"] != "measured"),
    "numeric_gate_pass": only is None and all(r["pass"] for r in results) and all(rest_gate.values()), "failed_motions": [r["id"] for r in results if not r["pass"]],
    "scope": "Numeric guards only, at finite poses: direction, real deformation of every stepped bone, triangle collapse, hand-region self and new "
             "cross-mesh intersections, hand edge-ratio guard, and a no-worse-than-baseline ratchet for the rest of the body (overlap at rest, pose-induced pairs and stretch). Weapon meshes are "
             "excluded here and judged by the grasp and clip gates. Not a continuous-range or art acceptance.",
    "results": results,
}
(out / "joint-range-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_JOINT_RANGE " + json.dumps({k: summary[k] for k in ("motions", "measured", "missing", "numeric_gate_pass", "calibration_run")} | {"failed": len(summary["failed_motions"])}))
