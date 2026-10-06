"""State-driven support correctives for the coat (Blender side). Mode 'press' (lying): the part of the coat that a
supine pose sinks into the support surface is pressed toward the body until it rests on the surface, its thick slab
squeezed. Mode 'fold' (seated): the skirt that hangs below the seat folds outward about the line where it meets the
surface and lies on it, as a long skirt spreads around a seated person.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_coat_lying.py -- \
       --contract <joint-range-contract.json> --rules-in <rules.json> --clip-blend <action .blend> --action <name> \
       --frame <f> --interaction <interaction.json> --tag <name> --out-dir <assets dir> [--copy <file> ...] \
       [--outer-offset-m 0.002] [--inner-offset-m 0.012] [--smooth-iterations 6] [--state lying] [--morph SKC_coat_lying]
       [--back-y-m 0.12] [--dilate-m 0.0] [--mode press|fold]
The pose is evaluated the way scripts/cv1_clip_check.py evaluates a clip sample (action at the frame, helpers,
interaction states of the config at that frame, correctives). Over the bed footprint every coat vertex must end at
least an offset above the bed top: the outer offset where its evaluated normal faces the surface, the inner offset
where it faces away (the slab's far side), in between on the rims. The lift is made in rest space along -Y (toward the
body, which a supine pose turns into straight up), as the distance s that reaches that height through the vertex's
skinning matrix. With --dilate-m each vertex first takes the largest need within that rest-space radius (a thin rim or hem
then lifts as one piece instead of folding over). The s field is softened by a few passes of 'the larger of the need and the mean of the neighbours'
(vertices at the same rest position move together), and held at zero on the waist (pelvis weight >= 0.5, which
includes the coat's bed-support vertices) and in front of --back-y-m. The result is one shape key driven by an
interaction state that clips declare with windows (zero in every frozen pose and every clip that does not declare it).
Weights, Basis and the other meshes are not touched; the input BLEND is not modified; a new BLEND, rules file and
report are written. Mode 'fold' instead moves each vertex that lies below its goal height by its depth d both up and
outward (--fold-dir back: toward the body's back, level; radial: away from the pelvis's vertical axis), so a hanging panel
turns onto the surface without losing
length; the d field is softened the same way, the inner side of the slab ends higher by the inner offset, only the
waist is held, and coat shape keys already present must be at zero in the design pose (b20's lying key while seated).
(The first version, a bend about a hinge at the back of the waist, is kept as
runs/qa/ro-swordsman-character-v1/v001/b20-prep/cv1_coat_lying-v1-used.py: near the hinge it needed 66 degrees and
stretched triangles twelvefold.)
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
parser.add_argument("--outer-offset-m", type=float, default=0.002)
parser.add_argument("--inner-offset-m", type=float, default=0.012)
parser.add_argument("--smooth-iterations", type=int, default=6)
parser.add_argument("--state", default="lying")
parser.add_argument("--morph", default="SKC_coat_lying")
parser.add_argument("--back-y-m", type=float, default=0.12)
parser.add_argument("--dilate-m", type=float, default=0.0, help="each vertex takes the largest need within this rest-space radius first (rims and hems lift as one)")
parser.add_argument("--mode", choices=("press", "fold"), default="press")
parser.add_argument("--fold-dir", choices=("radial", "back"), default="back", help="fold outward from the pelvis axis, or all toward the body's back")
parser.add_argument("--report-only", help="write the report to this path and save nothing else (parameter studies)")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists() and not args.report_only:
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
rules = json.loads((ROOT / args.rules_in).read_text(encoding="utf-8"))
config = interaction.load(ROOT / args.interaction)
bed = config["bed"]
fixtures_path = next((ROOT / c for c in args.copy if c.endswith("contact-fixtures.json")), None)
if args.state in {d.get("key") for d in rules["drivers"].values() if d["type"] == "state"} or args.state in rules["drivers"]:
    raise SystemExit(f"STATE_DRIVER_TAKEN {args.state}")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
coat = bpy.data.objects["SM_RO_coat"]
if coat.data.shape_keys is not None and args.mode == "press":
    raise SystemExit("COAT_ALREADY_HAS_SHAPE_KEYS (the press mode assumes the b19 coat without morphs)")
if coat.data.shape_keys is not None and args.morph in coat.data.shape_keys.key_blocks:
    raise SystemExit(f"MORPH_TAKEN {args.morph}")
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
arm.animation_data.action = None  # keep the evaluated pose; nothing below changes anything but the coat


def evaluated_coat():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = coat.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    points = [target.matrix_world @ v.co for v in mesh.vertices]
    normals = [(target.matrix_world.to_3x3() @ v.normal).normalized() for v in mesh.vertices]
    target.to_mesh_clear()
    return points, normals


def skin_matrix(index):
    blended = Matrix(((0,) * 4,) * 4)
    for g in coat.data.vertices[index].groups:
        name = group_names[g.group]
        if g.weight > 0 and name in bones:
            blended += (arm.pose.bones[name].matrix @ bones[name].matrix_local.inverted()) * g.weight
    return arm.matrix_world @ blended


if coat.data.shape_keys is not None and any(k.value != 0.0 for k in coat.data.shape_keys.key_blocks[1:]):
    raise SystemExit("COAT_KEYS_ACTIVE_IN_DESIGN_POSE (the new key is computed against the plain skinned coat)")
world, normals = evaluated_coat()
matrices = [skin_matrix(i) for i in range(n_vertices)]
skin_check = max((matrices[i] @ rest[i] - world[i]).length for i in range(n_vertices))
if skin_check > 1e-5:
    raise SystemExit(f"SKIN_MATRIX_MISMATCH {skin_check:.3e} m")
cx, cy = bed["centre_m"]
yaw = math.radians(bed["yaw_deg"])
half_l, half_w = bed["size_m"][0] / 2, bed["size_m"][1] / 2
top = bed["top_z_m"]


def over_bed(p):
    dx, dy = p.x - cx, p.y - cy
    return abs(dx * math.cos(yaw) + dy * math.sin(yaw)) <= half_l and abs(-dx * math.sin(yaw) + dy * math.cos(yaw)) <= half_w


# ---- frozen region, layer offsets and the need ----
pelvis_group = group_names.index("pelvis")
pelvis_weight = [next((g.weight for g in v.groups if g.group == pelvis_group), 0.0) for v in coat.data.vertices]
support_ids = []
if fixtures_path is not None:
    support_ids = list(json.loads(fixtures_path.read_text(encoding="utf-8"))["fixtures"]["bed_support.pelvis"]["ids"].get(coat.name, []))
anchored = np.array([pelvis_weight[i] >= 0.5 or (args.mode == "press" and rest[i].y < args.back_y_m) for i in range(n_vertices)])
pelvis_centre = arm.matrix_world @ arm.pose.bones["pelvis"].head
back = (arm.matrix_world.to_3x3() @ arm.pose.bones["pelvis"].matrix.to_3x3() @ bones["pelvis"].matrix_local.to_3x3().inverted() @ Vector((0.0, 1.0, 0.0)))
back = Vector((back.x, back.y, 0.0)).normalized()  # the body's back direction in the design pose, level
outward = []
for p in world:
    radial = Vector((p.x - pelvis_centre.x, p.y - pelvis_centre.y, 0.0))
    if args.fold_dir == "back":
        outward.append(back.copy())
    else:
        outward.append(radial.normalized() if radial.length > 1e-6 else Vector((0.0, 0.0, 0.0)))
need = np.zeros(n_vertices)
weak, anchored_sunk = [], []
for i in range(n_vertices):
    if not over_bed(world[i]):
        continue
    if args.mode == "press":
        # Facing the surface (normal down) -> outer offset; facing away -> inner offset; rims in between.
        facing_inner = min(1.0, max(0.0, (normals[i].z + 0.3) / 0.6))
    else:
        # A hanging skirt: its outer side faces away from the body, its inner side toward it.
        facing_inner = min(1.0, max(0.0, (-normals[i].dot(outward[i]) + 0.3) / 0.6))
    goal = top + args.outer_offset_m + (args.inner_offset_m - args.outer_offset_m) * facing_inner
    if world[i].z >= goal:
        continue
    if anchored[i]:
        anchored_sunk.append({"vertex": i, "below_goal_mm": round((goal - world[i].z) * 1e3, 2), "above_top_mm": round((world[i].z - top) * 1e3, 2)})
        continue
    if args.mode == "fold":
        need[i] = goal - world[i].z  # fold depth: the vertex moves this far up and this far outward
        continue
    lift_per_metre = -matrices[i][2][1]  # world z gained per metre moved along rest -Y
    if lift_per_metre < 0.3:
        weak.append({"vertex": i, "lift_per_metre": round(lift_per_metre, 3)})
        continue
    need[i] = (goal - world[i].z) / lift_per_metre

# ---- dilate: thin rims and hem edges take the largest need around them, so both faces of the slab lift together ----
if args.dilate_m > 0.0:
    from mathutils.kdtree import KDTree
    tree = KDTree(n_vertices)
    for i, p in enumerate(rest):
        tree.insert(p, i)
    tree.balance()
    dilated = need.copy()
    for i in np.nonzero(need > 0.0)[0]:
        for _, j, _ in tree.find_range(rest[int(i)], args.dilate_m):
            if not anchored[j]:
                dilated[j] = max(dilated[j], need[i])
    need = dilated

# ---- soften: welded nodes, a few passes of max(need, neighbour mean), zero on the frozen region ----
node_of, nodes = [], {}
for p in rest:
    node_of.append(nodes.setdefault(tuple(round(c, 6) for c in p), len(nodes)))
node_of = np.array(node_of)
n_nodes = len(nodes)
node_need = np.zeros(n_nodes)
np.maximum.at(node_need, node_of, need)
node_fixed = np.zeros(n_nodes, dtype=bool)
np.logical_or.at(node_fixed, node_of, anchored)
edges = np.array([[node_of[a], node_of[b]] for a, b in (e.vertices for e in coat.data.edges) if node_of[a] != node_of[b]])
degree = np.bincount(edges[:, 0], minlength=n_nodes) + np.bincount(edges[:, 1], minlength=n_nodes)
field = np.where(node_fixed, 0.0, node_need)
for _ in range(args.smooth_iterations):
    sums = np.bincount(edges[:, 0], weights=field[edges[:, 1]], minlength=n_nodes) + np.bincount(edges[:, 1], weights=field[edges[:, 0]], minlength=n_nodes)
    mean = np.where(degree > 0, sums / np.maximum(degree, 1), field)
    field = np.where(node_fixed, 0.0, np.maximum(node_need, mean))
s = field[node_of]

# ---- the shape key and the rule ----
if coat.data.shape_keys is None:
    coat.shape_key_add(name="Basis", from_mix=False)
key = coat.shape_key_add(name=args.morph, from_mix=False)
key.value = 0.0
conditioning = 0.0
for i in range(n_vertices):
    if s[i] <= 0.0:
        continue
    if args.mode == "press":
        key.data[i].co = rest[i] + Vector((0.0, -float(s[i]), 0.0))
    else:
        linear = matrices[i].to_3x3()
        conditioning = max(conditioning, float(np.linalg.cond(np.array(linear))))
        key.data[i].co = rest[i] + linear.inverted() @ ((outward[i] + Vector((0.0, 0.0, 1.0))) * float(s[i]))
rules["drivers"][args.state] = {"type": "state", "key": args.state}
rules["channels"].append({"mesh": coat.name, "morph": args.morph, "owner": "runtime_evaluator", "kind": "support_state", "driver": args.state, "curve": {"type": "linear"}})
rules["id"] = f"ro-swordsman-character-v1-v001-{args.tag}"
rules_math.validate_rules(rules)

# ---- check in the same pose with the key at the weight its state gives there (1) ----
key.value = 1.0
bpy.context.view_layer.update()
after, after_normals = evaluated_coat()
over_after = [p for p in after if over_bed(p)]
coat.data.calc_loop_triangles()
tris = [tuple(t.vertices) for t in coat.data.loop_triangles]


def area(points, t):
    a, b, c = (points[k] for k in t)
    return (b - a).cross(c - a).length / 2


rest_area = [area(rest, t) for t in tris]
ratio_before = [(area(world, t) / rest_area[k], k) for k, t in enumerate(tris) if rest_area[k] > 1e-10]
ratio_after = [(area(after, t) / rest_area[k], k) for k, t in enumerate(tris) if rest_area[k] > 1e-10]
worst = min(ratio_after)
moved = [i for i in range(n_vertices) if s[i] > 0.0]


def face_normal(points, t):
    a, b, c = (points[k] for k in t)
    return (b - a).cross(c - a)


# A triangle whose posed normal turns more than 90 degrees when the key comes on has folded over.
flipped = [k for k, t in enumerate(tris) if face_normal(world, t).length > 1e-12 and face_normal(after, t).length > 1e-12
           and face_normal(world, t).normalized().dot(face_normal(after, t).normalized()) < 0.0]
inner = [i for i in moved if normals[i].z > 0.3]
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__), "source": source,
    "inputs": {"contract": args.contract, "rules_in": {"path": args.rules_in, "sha256": sha(ROOT / args.rules_in)},
               "clip_blend": {"path": args.clip_blend, "sha256": sha(ROOT / args.clip_blend)}, "action": args.action, "frame": frame,
               "interaction": {"path": args.interaction, "sha256": sha(ROOT / args.interaction)}, "states_at_frame": state},
    "morph": args.morph, "state": args.state, "mode": args.mode, "fold_dir": args.fold_dir if args.mode == "fold" else None, "bed_top_z_m": top,
    "offsets_m": {"outer": args.outer_offset_m, "inner": args.inner_offset_m}, "smooth_iterations": args.smooth_iterations, "dilate_m": args.dilate_m,
    "frozen_region": {"pelvis_weight_at_least": 0.5, "in_front_of_y_m": args.back_y_m, "vertices": int(anchored.sum()), "coat_support_vertices": support_ids},
    "skin_matrix_check_m": skin_check, "fold_skin_condition_max": round(conditioning, 3),
    "sunk_before": {"vertices": int(sum(1 for p in world if over_bed(p) and p.z < top)),
                    "lowest_below_top_mm": round((top - min((p.z for p in world if over_bed(p)), default=top)) * 1e3, 2)},
    "after_lying_key": {"lowest_over_bed_above_top_mm": round((min(p.z for p in over_after) - top) * 1e3, 3),
                        "vertices_below_top": int(sum(1 for p in over_after if p.z < top))},
    "anchored_below_goal": anchored_sunk[:20], "anchored_below_goal_count": len(anchored_sunk), "weak_direction": weak[:20], "weak_direction_count": len(weak),
    "lift": {"vertices": len(moved), "max_rest_offset_mm": round(float(s.max()) * 1e3, 2)},
    "support_vertices_offset_mm": [round(float(s[i]) * 1e3, 6) for i in support_ids],
    "coat_triangle_area_ratio_in_pose": {"min_without_key": round(min(ratio_before)[0], 4), "min_with_key": round(worst[0], 4),
                                         "max_with_key": round(max(ratio_after)[0], 4),
                                         "worst_triangle": {"index": worst[1], "rest_centre_m": [round(c, 4) for c in sum((rest[k] for k in tris[worst[1]]), Vector()) / 3]},
                                         "triangles_below_0.05": sum(1 for r, _ in ratio_after if r < 0.05),
                                         "triangles_below_0.10": sum(1 for r, _ in ratio_after if r < 0.10),
                                         "max_without_key": round(max(ratio_before)[0], 4)},
    "flipped_when_key_on": len(flipped),
    "inner_side_lifted": {"vertices": len(inner), "max_above_top_mm": round((max((after[i].z for i in inner), default=top) - top) * 1e3, 2)},
    "scope": "Coat only. Zero in every pose whose interaction state is zero (every frozen contract pose and every clip that does not declare the state).",
}
if args.report_only:
    Path(args.report_only).write_text(json.dumps(report, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
    print("CV1_COAT_LYING_STUDY " + json.dumps({k: report[k] for k in ("after_lying_key", "lift", "coat_triangle_area_ratio_in_pose", "flipped_when_key_on", "inner_side_lifted")}))
    raise SystemExit(0)
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
print("CV1_COAT_LYING " + json.dumps({k: report[k] for k in ("sunk_before", "after_lying_key", "anchored_below_goal_count", "weak_direction_count", "lift",
                                                            "support_vertices_offset_mm", "coat_triangle_area_ratio_in_pose", "flipped_when_key_on", "inner_side_lifted")}))
