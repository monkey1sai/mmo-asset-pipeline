"""State-driven 'lying' corrective for the coat: the back panel that a supine pose sinks into the support surface is
bent forward about a hinge at the back of the waist until it rests on the surface (Blender side).

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_coat_lying.py -- \
       --contract <joint-range-contract.json> --rules-in <rules.json> --clip-blend <action .blend> --action <name> \
       --frame <f> --interaction <interaction.json> --tag <name> --out-dir <assets dir> [--copy <file> ...] \
       [--margin-m 0.002] [--state lying] [--morph SKC_coat_lying] [--hinge-z-m 0.77] [--back-y-m 0.12]
The pose is evaluated the way scripts/cv1_clip_check.py evaluates a clip sample (action at the frame, helpers,
interaction states of the config at that frame, correctives). Each coat vertex over the bed footprint that lies below
the bed top plus the margin gets the smallest bend that lifts it there: a turn about the rest-space X axis through
the hinge (y = mean of the coat's pelvis bed-support vertices, z = --hinge-z-m), toward the front, so the panel keeps
its size. The bend angles are spread over the coat as the smallest field at or above every need and harmonic
elsewhere (vertices at the same rest position move together), held at zero on the waist (pelvis weight >= 0.5, which
includes the coat's bed-support vertices), above the hinge, and in front of --back-y-m. The bent rest positions are
stored as one shape key driven by an interaction state that clips declare with windows (zero in every frozen pose and
every clip that does not declare it). Weights, Basis and the other meshes are not touched; the input BLEND is not
modified; a new BLEND, rules file and report are written.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math

parser = argparse.ArgumentParser()
for name in ("--contract", "--rules-in", "--clip-blend", "--action", "--frame", "--interaction", "--tag", "--out-dir"):
    parser.add_argument(name, required=True)
parser.add_argument("--copy", nargs="*", default=[], help="files copied unchanged into the new foundation folder (poses, contact fixtures)")
parser.add_argument("--margin-m", type=float, default=0.002)
parser.add_argument("--state", default="lying")
parser.add_argument("--morph", default="SKC_coat_lying")
parser.add_argument("--hinge-z-m", type=float, default=0.77)
parser.add_argument("--back-y-m", type=float, default=0.12)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules_in).read_text(encoding="utf-8"))
config = interaction.load(ROOT / args.interaction)
bed = config["bed"]
fixtures_path = next((ROOT / c for c in args.copy if c.endswith("contact-fixtures.json")), None)
if args.state in {d.get("key") for d in rules["drivers"].values() if d["type"] == "state"} or args.state in rules["drivers"]:
    raise SystemExit(f"STATE_DRIVER_TAKEN {args.state}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
coat = bpy.data.objects["SM_RO_coat"]
if coat.data.shape_keys is not None:
    raise SystemExit("COAT_ALREADY_HAS_SHAPE_KEYS (this builder assumes the b19 coat without morphs)")
if any(m.type == "ARMATURE" and m.use_deform_preserve_volume for m in coat.modifiers):
    raise SystemExit("COAT_USES_DUAL_QUATERNION_SKINNING (the inverse below is linear-blend only)")
group_names = [g.name for g in coat.vertex_groups]
rest = [v.co.copy() for v in coat.data.vertices]
n_vertices = len(rest)
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def zero_keys():
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0


# ---- the supine pose: action, helpers, states, correctives (as the clip check evaluates a sample) ----
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (src, dst):
    dst.actions = [args.action]
action = dst.actions[0]
arm.animation_data_create()
arm.animation_data.action = action
frame = float(args.frame)
bpy.context.scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
bpy.context.view_layer.update()
pose = pose_rel()
for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
    arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
    pose[name] = quaternion
bpy.context.view_layer.update()
states = interaction.states_at(config, frame)
state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
zero_keys()
for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
    bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
bpy.context.view_layer.update()
# Freeze the pose: the action is detached so the solve below can change nothing but the coat.
arm.animation_data.action = None


def evaluated_coat():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = coat.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    points = [target.matrix_world @ v.co for v in mesh.vertices]
    target.to_mesh_clear()
    return points


def skin_matrix(index):
    blended = Matrix(((0,) * 4,) * 4)
    for g in coat.data.vertices[index].groups:
        name = group_names[g.group]
        if g.weight > 0 and name in bones:
            blended += (arm.pose.bones[name].matrix @ bones[name].matrix_local.inverted()) * g.weight
    return arm.matrix_world @ blended


world = evaluated_coat()
matrices = [skin_matrix(i) for i in range(n_vertices)]
skin_check = max((matrices[i] @ rest[i] - world[i]).length for i in range(n_vertices))
if skin_check > 1e-5:
    raise SystemExit(f"SKIN_MATRIX_MISMATCH {skin_check:.3e} m")
cx, cy = bed["centre_m"]
yaw = math.radians(bed["yaw_deg"])
half_l, half_w = bed["size_m"][0] / 2, bed["size_m"][1] / 2
target_z = bed["top_z_m"] + args.margin_m


def over_bed(p):
    dx, dy = p.x - cx, p.y - cy
    return abs(dx * math.cos(yaw) + dy * math.sin(yaw)) <= half_l and abs(-dx * math.sin(yaw) + dy * math.cos(yaw)) <= half_w


# ---- the hinge and the frozen region ----
pelvis_group = group_names.index("pelvis")
pelvis_weight = [next((g.weight for g in v.groups if g.group == pelvis_group), 0.0) for v in coat.data.vertices]
support_ids = []
if fixtures_path is not None:
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))["fixtures"]
    support_ids = list(fixtures["bed_support.pelvis"]["ids"].get(coat.name, []))
hinge_y = sum(rest[i].y for i in support_ids) / len(support_ids) if support_ids else 0.207
hinge = Vector((0.0, hinge_y, args.hinge_z_m))
anchored = [pelvis_weight[i] >= 0.5 or rest[i].z >= args.hinge_z_m or rest[i].y < args.back_y_m for i in range(n_vertices)]


def bent(i, theta):
    """Rest position of vertex i turned toward the front by theta about the X axis through the hinge."""
    offset = rest[i] - hinge
    return hinge + Matrix.Rotation(-theta, 3, "X") @ Vector((0.0, offset.y, offset.z)) + Vector((offset.x, 0.0, 0.0))


def lifted_z(i, theta):
    return (matrices[i] @ bent(i, theta)).z


# ---- the smallest bend each sunk vertex needs ----
need = np.zeros(n_vertices)
unreachable, anchored_sunk = [], []
for i in range(n_vertices):
    if not over_bed(world[i]) or world[i].z >= target_z:
        continue
    if anchored[i]:
        anchored_sunk.append({"vertex": i, "depth_mm": round((target_z - world[i].z) * 1e3, 2)})
        continue
    low, high = 0.0, math.radians(90.0)
    if lifted_z(i, high) < target_z:
        unreachable.append({"vertex": i, "depth_mm": round((target_z - world[i].z) * 1e3, 2)})
        need[i] = high
        continue
    for _ in range(40):
        mid = (low + high) / 2
        if lifted_z(i, mid) < target_z:
            low = mid
        else:
            high = mid
    need[i] = high

# ---- spread the bend: welded nodes, obstacle field (>= need, harmonic elsewhere), zero on the frozen region ----
node_of, nodes = [], {}
for p in rest:
    node_of.append(nodes.setdefault(tuple(round(c, 6) for c in p), len(nodes)))
node_of = np.array(node_of)
n_nodes = len(nodes)
node_need = np.zeros(n_nodes)
np.maximum.at(node_need, node_of, need)
node_fixed = np.zeros(n_nodes, dtype=bool)
np.logical_or.at(node_fixed, node_of, np.array(anchored))
edges = np.array([[node_of[a], node_of[b]] for a, b in (e.vertices for e in coat.data.edges) if node_of[a] != node_of[b]])
degree = np.bincount(edges[:, 0], minlength=n_nodes) + np.bincount(edges[:, 1], minlength=n_nodes)
field = node_need.copy()
iterations = 0
for iterations in range(1, 20001):
    sums = np.bincount(edges[:, 0], weights=field[edges[:, 1]], minlength=n_nodes) + np.bincount(edges[:, 1], weights=field[edges[:, 0]], minlength=n_nodes)
    mean = np.where(degree > 0, sums / np.maximum(degree, 1), field)
    new = np.where(node_fixed, 0.0, np.maximum(node_need, mean))
    change = float(np.max(np.abs(new - field)))
    field = new
    if change < 1e-9:
        break
theta = field[node_of]

# ---- the shape key and the rule ----
coat.shape_key_add(name="Basis", from_mix=False)
key = coat.shape_key_add(name=args.morph, from_mix=False)
for i in range(n_vertices):
    if theta[i] > 0.0:
        key.data[i].co = bent(i, float(theta[i]))
rules["drivers"][args.state] = {"type": "state", "key": args.state}
rules["channels"].append({"mesh": coat.name, "morph": args.morph, "owner": "runtime_evaluator", "kind": "support_state", "driver": args.state, "curve": {"type": "linear"}})
rules["id"] = f"ro-swordsman-character-v1-v001-{args.tag}"
rules_math.validate_rules(rules)

# ---- check in the same pose: the key at the weight the state gives while lying (1) ----
key.value = 1.0
bpy.context.view_layer.update()
after = evaluated_coat()
over_after = [p for p in after if over_bed(p)]
coat.data.calc_loop_triangles()
tris = [tuple(t.vertices) for t in coat.data.loop_triangles]


def area(points, t):
    a, b, c = (points[k] for k in t)
    return (b - a).cross(c - a).length / 2


rest_area = [area(rest, t) for t in tris]
ratios_before = [area(world, t) / rest_area[k] for k, t in enumerate(tris) if rest_area[k] > 1e-10]
ratios_after = [area(after, t) / rest_area[k] for k, t in enumerate(tris) if rest_area[k] > 1e-10]
moved = [i for i in range(n_vertices) if theta[i] > 0.0]
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__), "source": source,
    "inputs": {"contract": args.contract, "rules_in": {"path": args.rules_in, "sha256": sha(ROOT / args.rules_in)},
               "clip_blend": {"path": args.clip_blend, "sha256": sha(ROOT / args.clip_blend)}, "action": args.action, "frame": frame,
               "interaction": {"path": args.interaction, "sha256": sha(ROOT / args.interaction)}, "states_at_frame": state},
    "morph": args.morph, "state": args.state, "margin_m": args.margin_m, "bed_top_z_m": bed["top_z_m"],
    "hinge_rest_m": list(hinge), "frozen_region": {"pelvis_weight_at_least": 0.5, "above_hinge_z_m": args.hinge_z_m, "in_front_of_y_m": args.back_y_m,
                                                   "vertices": int(sum(anchored)), "coat_support_vertices": support_ids},
    "skin_matrix_check_m": skin_check, "field_iterations": iterations, "field_last_change_rad": change,
    "sunk_before": {"vertices": int(sum(1 for p in world if over_bed(p) and p.z < bed["top_z_m"])),
                    "lowest_below_top_mm": round((bed["top_z_m"] - min((p.z for p in world if over_bed(p)), default=bed["top_z_m"])) * 1e3, 2)},
    "after_lying_key": {"lowest_over_bed_above_top_mm": round((min(p.z for p in over_after) - bed["top_z_m"]) * 1e3, 3),
                        "vertices_below_target": int(sum(1 for p in over_after if p.z < target_z - 1e-5))},
    "anchored_but_sunk": anchored_sunk[:20], "anchored_but_sunk_count": len(anchored_sunk), "unreachable": unreachable[:20], "unreachable_count": len(unreachable),
    "bend": {"vertices": len(moved), "max_deg": round(math.degrees(float(theta.max())), 3),
             "max_rest_offset_mm": round(max(((key.data[i].co - rest[i]).length for i in moved), default=0.0) * 1e3, 2)},
    "support_vertices_offset_mm": [round((key.data[i].co - rest[i]).length * 1e3, 6) for i in support_ids],
    "coat_triangle_area_ratio_in_pose": {"min_without_key": round(min(ratios_before), 4), "min_with_key": round(min(ratios_after), 4),
                                         "max_with_key": round(max(ratios_after), 4)},
    "scope": "Coat only. Zero in every pose whose interaction state is zero (every frozen contract pose and every clip that does not declare the state).",
}
rules_out = out_dir / "corrective-rules.json"
out_dir.mkdir(parents=True)
key.value = 0.0
zero_keys()
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
bpy.data.actions.remove(action)
bpy.context.view_layer.update()
rules_out.write_text(json.dumps(rules, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
blend_path = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
copied = {}
for name in args.copy:
    target_path = out_dir / Path(name).name
    shutil.copyfile(ROOT / name, target_path)
    copied[Path(name).name] = {"from": name, "sha256": sha(target_path)}
report.update({"output": {"blend": {"path": blend_path.relative_to(ROOT).as_posix(), "sha256": sha(blend_path)},
                          "rules": {"path": rules_out.relative_to(ROOT).as_posix(), "sha256": sha(rules_out)}, "copied": copied},
               "source_sha256_after": sha(ROOT / source["path"])})
(out_dir / "coat-lying-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_COAT_LYING " + json.dumps({k: report[k] for k in ("sunk_before", "after_lying_key", "anchored_but_sunk_count", "unreachable_count", "bend",
                                                            "support_vertices_offset_mm", "coat_triangle_area_ratio_in_pose", "field_iterations")}))
