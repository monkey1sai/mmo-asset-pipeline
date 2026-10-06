"""Pose-driven correctives for the hands of a character V1 candidate.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_hand_correctives.py -- \
       --contract <joint-range-contract.json> --rules-in <rules.json> --tag <name> --out-dir <assets dir of the candidate>
Three stages, all stored as shape keys in rest space (inverse of each vertex's blended skin matrix) and driven by
joint rotation only; Basis, topology, UVs and weights are not touched:
  1. crease relief per joint: each finger, thumb and wrist-flexion joint is posed alone at the contract's extreme
     and the skin around the crease is relaxed until no edge is squeezed or stretched past the strain limits;
  2. clearance between neighbouring fingers at the contract poses where they meet, driven by both fingers bending;
  3. a residual relief at the full fist, driven by the middle finger's two main joints bending together.
The right hand is authored and the left receives the mirror image. The input BLEND is not modified; a new BLEND
and rules file are written and existing outputs are refused.
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
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math

parser = argparse.ArgumentParser()
parser.add_argument("--contract", required=True)
parser.add_argument("--rules-in", required=True)
parser.add_argument("--tag", required=True)
parser.add_argument("--out-dir", required=True)
parser.add_argument("--low", type=float, default=0.45)
parser.add_argument("--high", type=float, default=2.2)
parser.add_argument("--iterations", type=int, default=80)
parser.add_argument("--clearance-step-mm", type=float, default=0.2)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")
out_dir.mkdir(parents=True)
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules_in).read_text(encoding="utf-8"))
motions = {m["id"]: m for m in contract["motions"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
right, left = bpy.data.objects["SM_RO_hand.R"], bpy.data.objects["SM_RO_hand.L"]
assert len(right.data.vertices) == len(left.data.vertices)
keys_before = [k.name for k in right.data.shape_keys.key_blocks]


def hand_frame():
    wrist = bones["hand.R"].head_local
    mcp = {i: bones[f"finger{i}.R_01"].head_local for i in (1, 2, 3, 4)}
    thumb = bones["thumb.R_01"].head_local
    index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
    along = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
    across = mcp[index] - mcp[pinky]
    radial = (across - along * across.dot(along)).normalized()
    palmar = radial.cross(along).normalized()
    return {"palmar": palmar, "dorsal": -palmar, "radial": radial, "ulnar": -radial}


FRAME = hand_frame()


def step_quaternion(step, level=1.0):
    bone = bones[step["bone"]]
    axis = (bone.tail_local - bone.head_local).normalized().cross(FRAME[step["toward"]]).normalized()
    return Quaternion(bone.matrix_local.to_3x3().inverted() @ axis, math.radians(step["degrees"]) * level)


# One entry per right-hand joint that gets crease relief: the contract's own single-joint step for that bone.
joints = {}
for motion in contract["motions"]:
    if motion["region"] == "hand.R":
        for step in motion["steps"]:
            digit = step["bone"].startswith(("finger", "thumb")) and step["kind"] == "swing" and ("flexion" in motion["id"] or "opposition" in motion["id"])
            if digit or motion["id"] == "wrist-flexion.R":
                joints[step["bone"]] = step
assert len(joints) == 16, sorted(joints)
PARENT_GROUP = {name: bones[name].parent.name for name in joints}
PARENT_GROUP["hand.R"] = "wrist_transition.R_twist"  # the cuff next to the wrist is carried by this bone, not by the forearm itself

mesh = right.data
group_names = [g.name for g in right.vertex_groups]
vertex_weights = [{group_names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in mesh.vertices]
dominant = [max(w, key=w.get) for w in vertex_weights]
edges = [tuple(e.vertices) for e in mesh.edges]
neighbours = [[] for _ in mesh.vertices]
for a, b in edges:
    neighbours[a].append(b)
    neighbours[b].append(a)
basis = [v.co.copy() for v in mesh.vertices]
rest_length = [(basis[a] - basis[b]).length for a, b in edges]
mesh.calc_loop_triangles()
tris = [tuple(t.vertices) for t in mesh.loop_triangles]
position_keys = {}
canonical = [position_keys.setdefault(tuple(round(c, 7) for c in p), len(position_keys)) for p in basis]


def reset():
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    for obj in (right, left):
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0
    bpy.context.view_layer.update()


def pose_rel():
    out = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        out[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return out


def apply_rules():
    """Set every existing right-hand key from the current rules and pose; returns the driver values."""
    pose = pose_rel()
    state = {d["key"]: 0.0 for d in rules["drivers"].values() if d["type"] == "state"}
    blocks = right.data.shape_keys.key_blocks
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        if mesh_name == right.name and key_name in blocks:
            blocks[key_name].value = value
    bpy.context.view_layer.update()
    return rules_math.driver_values(rules, pose, state)


def set_motion(motion_id, level):
    reset()
    for step in motions[motion_id]["steps"]:
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ step_quaternion(step, level)
    bpy.context.view_layer.update()
    return apply_rules()


def evaluated():
    target = right.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = target.to_mesh()
    points, normals = [v.co.copy() for v in data.vertices], [v.normal.copy() for v in data.vertices]
    target.to_mesh_clear()
    return points, normals


def skin_matrices():
    skin = {name: (arm.pose.bones[name].matrix @ bones[name].matrix_local.inverted()) for name in group_names if name in bones}
    out = []
    for weights in vertex_weights:
        blended = Matrix(((0,) * 4,) * 4)
        for name, weight in weights.items():
            blended += skin[name] * weight
        out.append(blended)
    return out


def rest_delta(matrix, desired, label):
    linear = matrix.to_3x3()
    condition = float(np.linalg.cond(np.array(linear)))
    if condition > 20:
        raise SystemExit(f"UNSTABLE_INVERSE_SKIN {label} condition {condition:.1f}")
    return linear.inverted() @ desired


def relax(points, region):
    """Strain-limit edges that touch the region; only region vertices move. Returns (relaxed, before, after) ratio ranges."""
    relaxed = [p.copy() for p in points]
    region_edges = [(k, a, b) for k, (a, b) in enumerate(edges) if (a in region or b in region) and rest_length[k] > 1e-6]
    ratio = lambda: [(relaxed[a] - relaxed[b]).length / rest_length[k] for k, a, b in region_edges]
    before = ratio()
    for _ in range(args.iterations):
        moves = {}
        for k, a, b in region_edges:
            delta = relaxed[a] - relaxed[b]
            length = delta.length
            target = min(max(length, args.low * rest_length[k]), args.high * rest_length[k])
            if abs(target - length) < 1e-9 or length < 1e-9:
                continue
            push = delta * ((target - length) / length)
            share = [v for v in (a, b) if v in region]
            for vertex in share:
                moves.setdefault(vertex, []).append(push / len(share) * (1 if vertex == a else -1))
        if not moves:
            break
        for vertex, pushes in moves.items():
            relaxed[vertex] += sum(pushes, Vector()) / len(pushes) * 0.6
    after = ratio()
    return relaxed, [round(min(before), 3), round(max(before), 3)], [round(min(after), 3), round(max(after), 3)]


def add_rule(key_name, driver_name, driver):
    rules["drivers"].setdefault(driver_name, driver)
    rules["channels"].append({"mesh": right.name, "morph": key_name, "owner": "runtime_evaluator", "kind": "body_pose", "driver": driver_name, "curve": {"type": "linear"}})


def grow(seed, rings):
    region = set(seed)
    for _ in range(rings):
        region |= {n for i in region for n in neighbours[i]}
    return region


# ---- stage 1: crease relief per joint ----
reset()
stage1 = []
blend_zones = {}
for bone_name, step in sorted(joints.items()):
    parent_group = PARENT_GROUP[bone_name]
    blend = {i for i, w in enumerate(vertex_weights) if w.get(bone_name, 0) > 0.05 and w.get(parent_group, 0) > 0.05}
    blend_zones[bone_name] = blend
    region = grow(blend, 2)
    rotation = step_quaternion(step)
    reset()
    arm.pose.bones[bone_name].rotation_quaternion = rotation
    bpy.context.view_layer.update()
    matrices = skin_matrices()
    posed = [matrices[i] @ basis[i] for i in range(len(basis))]
    relaxed, before, after = relax(posed, region)
    key = right.shape_key_add(name=f"SKC_{bone_name}", from_mix=False)
    moved, largest = 0, 0.0
    for index in region:
        desired = relaxed[index] - posed[index]
        if desired.length >= 1e-7:
            delta = rest_delta(matrices[index], desired, bone_name)
            key.data[index].co = basis[index] + delta
            moved, largest = moved + 1, max(largest, delta.length)
    add_rule(key.name, f"flex.{bone_name}", {"type": "rotation_difference", "bone": bone_name, "target_quaternion_wxyz": list(rotation),
                                              "target_source": f"contract step {step['toward']} {step['degrees']} degrees"})
    stage1.append({"bone": bone_name, "blend_zone_vertices": len(blend), "vertices_moved": moved, "largest_rest_delta_mm": round(largest * 1e3, 3),
                   "edge_ratio_before": before, "edge_ratio_after": after})


def fingers_of(pair):
    """The one or two fingers a touching pair belongs to, or None when the palm, thumb or three fingers are involved."""
    names = [dominant[i] for triangle in pair for i in tris[triangle]]
    fingers = sorted({int(n[6]) for n in names if n.startswith("finger")})
    if not all(n.startswith("finger") for n in names) or len(fingers) > 2:
        return None
    return (fingers[0], fingers[-1])


def self_pairs(points):
    tree = BVHTree.FromPolygons(points, tris, all_triangles=True, epsilon=0.0)
    return [(a, b) for a, b in tree.overlap(tree) if a < b and not ({canonical[i] for i in tris[a]} & {canonical[i] for i in tris[b]})]


# ---- stage 2: clearance between neighbouring fingers where the contract poses bring them together ----
stage2 = []
step_m = args.clearance_step_mm / 1000
for motion_id, joint_index in (("fingers-mcp-flexion.R", 1), ("combo-empty-fist.R", 2)):
    level = contract["levels"]["typical"]
    row = {"pose": motion_id, "level": level, "iterations": 0, "keys": []}
    for iteration in range(25):
        drivers = set_motion(motion_id, level)
        points, normals = evaluated()
        pairs = self_pairs(points)
        between = [pair for pair in pairs if fingers_of(pair)]
        if iteration == 0:
            row["pairs_before"], row["finger_pairs_before"] = len(pairs), len(between)
        row["pairs_after"], row["finger_pairs_after"], row["iterations"] = len(pairs), len(between), iteration
        if not between:
            break
        matrices = skin_matrices()
        by_key = {}
        for a, b in between:
            by_key.setdefault(fingers_of((a, b)), set()).update(tris[a] + tris[b])
        for (low_finger, high_finger), vertices in by_key.items():
            key_name = f"SKC_clear_{low_finger}{high_finger}_j{joint_index}.R"
            driver_name = f"both.{low_finger}{high_finger}_j{joint_index}.R"
            factors = [f"flex.finger{low_finger}.R_0{joint_index}", f"flex.finger{high_finger}.R_0{joint_index}"]
            blocks = right.data.shape_keys.key_blocks
            if key_name not in blocks:
                right.shape_key_add(name=key_name, from_mix=False)
                add_rule(key_name, driver_name, {"type": "product", "of": factors})
                row["keys"].append(key_name)
            weight = drivers[factors[0]] * drivers[factors[1]]
            key = blocks[key_name]
            for index in grow(vertices, 1):
                # Pull the touching sides in along their own normals; stored so that the pose's driver value reproduces this offset.
                key.data[index].co = key.data[index].co + rest_delta(matrices[index], -normals[index] * step_m, key_name) / weight
    stage2.append(row)

# ---- stage 3: residual relief at the full fist ----
drivers = set_motion("combo-empty-fist.R", contract["levels"]["extreme"])
points, _ = evaluated()
region = grow(set().union(*(blend_zones[name] for name in joints if name != "hand.R")), 2)
relaxed, before, after = relax(points, region)
# Triangles that fold flat at the full fist get a minimum area back: the vertex opposite the longest edge moves away from that edge.
rest_area = [(basis[b] - basis[a]).cross(basis[c] - basis[a]).length / 2 for a, b, c in tris]
area_fixed = set()
for _ in range(40):
    flat = [k for k, (a, b, c) in enumerate(tris) if rest_area[k] > 1e-10 and (relaxed[b] - relaxed[a]).cross(relaxed[c] - relaxed[a]).length / 2 < 0.10 * rest_area[k]]
    if not flat:
        break
    for k in flat:
        corners = list(tris[k])
        base = list(max(((corners[i], corners[j]) for i in range(3) for j in range(i + 1, 3)), key=lambda e: (relaxed[e[0]] - relaxed[e[1]]).length))
        apex = next(v for v in corners if v not in base)
        edge = (relaxed[base[1]] - relaxed[base[0]]).normalized()
        offset = relaxed[apex] - relaxed[base[0]]
        away = offset - edge * offset.dot(edge)
        if away.length < 1e-7:
            away = (basis[apex] - basis[base[0]]) - (basis[base[1]] - basis[base[0]]).normalized() * (basis[apex] - basis[base[0]]).dot((basis[base[1]] - basis[base[0]]).normalized())
        relaxed[apex] += away.normalized() * 0.0002
        area_fixed.add(k)
region |= {v for k in area_fixed for v in tris[k]}
matrices = skin_matrices()
fist_key = right.shape_key_add(name="SKC_fist.R", from_mix=False)
add_rule(fist_key.name, "both.fist.R", {"type": "product", "of": ["flex.finger3.R_01", "flex.finger3.R_02"]})
fist_weight = drivers["flex.finger3.R_01"] * drivers["flex.finger3.R_02"]
moved = 0
for index in region:
    desired = relaxed[index] - points[index]
    if desired.length >= 1e-7:
        fist_key.data[index].co = basis[index] + rest_delta(matrices[index], desired, "fist") / fist_weight
        moved += 1
stage3 = {"vertices_moved": moved, "flat_triangles_given_area": len(area_fixed), "driver_value_at_extreme": fist_weight, "edge_ratio_before": before, "edge_ratio_after": after}

# ---- what the contract poses look like with everything applied (the sweep remains the judge) ----
check = {}
for motion_id in ("fingers-mcp-flexion.R", "fingers-pip-flexion.R", "combo-empty-fist.R"):
    for level_name, level in contract["levels"].items():
        set_motion(motion_id, level)
        points, _ = evaluated()
        ratios = [(points[a] - points[b]).length / length for (a, b), length in zip(edges, rest_length) if length > 1e-6]
        check[f"{motion_id}/{level_name}"] = {"self_pairs": len(self_pairs(points)), "edge_ratio": [round(min(ratios), 3), round(max(ratios), 3)]}
reset()

# ---- mirror keys and rules to the left hand ----
new_keys = [k for k in right.data.shape_keys.key_blocks if k.name not in keys_before]
for key in new_keys:
    mirrored = left.shape_key_add(name=key.name.replace(".R", ".L"), from_mix=False)
    for index in range(len(basis)):
        co = key.data[index].co
        mirrored.data[index].co = Vector((-co.x, co.y, co.z))
for name, driver in list(rules["drivers"].items()):
    if ".R" in name and name.replace(".R", ".L") not in rules["drivers"] and driver["type"] != "state":
        twin = json.loads(json.dumps(driver).replace(".R", ".L"))
        if twin["type"] == "rotation_difference":
            w, x, y, z = driver["target_quaternion_wxyz"]
            twin["target_quaternion_wxyz"] = [w, x, -y, -z]
        rules["drivers"][name.replace(".R", ".L")] = twin
for channel in list(rules["channels"]):
    if channel["mesh"] == right.name and channel["morph"] in {k.name for k in new_keys}:
        rules["channels"].append(json.loads(json.dumps(channel).replace(".R", ".L")))
rules["id"] = f"ro-swordsman-character-v1-v001-{args.tag}"
rules_math.validate_rules(rules)
(out_dir / "corrective-rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
basis_unchanged = all((v.co - b).length == 0 for v, b in zip(right.data.vertices, basis))
blend_path = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "source": source, "source_sha256_after": sha(ROOT / source["path"]),
           "output": {"path": blend_path.relative_to(ROOT).as_posix(), "sha256": sha(blend_path)},
           "limits": {"low": args.low, "high": args.high, "iterations": args.iterations, "clearance_step_mm": args.clearance_step_mm},
           "right_basis_unchanged": basis_unchanged, "shape_keys_added_per_hand": len(new_keys),
           "stage1_crease_relief": stage1, "stage2_finger_clearance": stage2, "stage3_fist_residual": stage3, "contract_pose_check": check,
           "scope": "Edge-length relief and side clearance only. No flesh contact or volume model, and not an art acceptance."}
(out_dir / "hand-correctives-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_HAND_CORRECTIVES", json.dumps({"keys": len(new_keys), "basis_unchanged": basis_unchanged, "stage2": [{k: r[k] for k in ("pose", "finger_pairs_before", "finger_pairs_after", "pairs_after", "iterations")} for r in stage2],
                                           "stage3": stage3, "check": check}))
