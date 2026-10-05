"""Candidate v001 foundation: bring the r010 right hand into the whole character and mirror it for the left.

Run: blender -b --factory-startup --disable-autoexec <ro_whole_baseline.blend> --python scripts/cv1_v001_assemble.py -- --tag <name> [--cuff-blend-mm N]
The baseline and r010 files are only read; the result is saved as a new BLEND and existing outputs are refused.

The r010 hand moves as one rigid unit: mesh, its 16 bone frames and its weapon socket share one registration
transform, so its shape, weights, UVs and the bone-local pose data stay valid. --cuff-blend-mm reweights the
cuff behind the wrist toward the forearm; that edits protected r010 weights and needs a recorded authorization.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--tag", required=True)
parser.add_argument("--cuff-blend-mm", type=float)
parser.add_argument("--stump-cut-mm", type=float, default=-25.41, help="where both forearm stumps of the core end, along the forearm from the wrist")
parser.add_argument("--toe-blend-mm", type=float)
parser.add_argument("--hand-material", action="store_true")
parser.add_argument("--twist-fade-mm", type=float, default=12.0)
parser.add_argument("--toe-radius-mm", type=float, default=1000.0)
parser.add_argument("--left-bracer", choices=("mirror", "cut"), default="mirror")
parser.add_argument("--relax-core", help="x,y,z;x,y,z rest positions where core weights are smoothed locally")
parser.add_argument("--relax-radius-mm", type=float, default=35.0)
parser.add_argument("--rigid-core", help="x,y,z;x,y,z rest centroids of core triangles whose three vertices get one shared weight set")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
HAND_BLEND = ROOT / "assets/processed/ro-swordsman-combo-r010/v004-certified-animation/right_hand_grasp_61f.blend"
OUT = ROOT / "assets/processed/ro-swordsman-character-v1/v001" / args.tag
QA = ROOT / "runs/qa/ro-swordsman-character-v1/v001" / args.tag
if OUT.exists() or QA.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {args.tag}")
if args.cuff_blend_mm is not None:
    record = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1/authorizations.json").read_text(encoding="utf-8"))
    if record["protected_zone"].get("D_cuff_weights") != "authorized":
        raise SystemExit("CUFF_REWEIGHT_NOT_AUTHORIZED")
OUT.mkdir(parents=True)
QA.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
with bpy.data.libraries.load(str(HAND_BLEND), link=False) as (available, wanted):
    wanted.objects = ["ARM_RO_HandDiagnostic", "SM_RO_RightHand_Exterior", "SM_RO_LocalActualSword"]
    wanted.actions = ["AN_RO_RightHand_GraspDiagnostic"]
hand_arm, hand, local_sword = wanted.objects
grasp_action = wanted.actions[0]
arm = bpy.data.objects["ARM_RO_Swordsman"]
collection = arm.users_collection[0]
hb = hand_arm.data.bones
MIRROR = Matrix.Diagonal((-1, 1, 1, 1))

# Prototype clips are not part of the character foundation.
arm.animation_data_clear()
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0


def hand_basis(bones, hand_name, finger_name, thumb_name):
    """Orthonormal (radial, along, palmar) of a right hand from its joints, and the wrist point."""
    wrist = bones[hand_name].head_local.copy()
    mcp = {i: bones[finger_name.format(i=i)].head_local for i in (1, 2, 3, 4)}
    thumb = bones[thumb_name].head_local
    index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
    along = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
    across = mcp[index] - mcp[pinky]
    radial = (across - along * across.dot(along)).normalized()
    return wrist, radial, along, radial.cross(along).normalized()


# ---- registration: r010 hand space -> armature space, rigid, no scale ----
wrist0, radial0, along0, palmar0 = hand_basis(hb, "hand", "finger{i}_01", "thumb_01")
wrist, _, _, palmar_base = hand_basis(arm.data.bones, "hand.R", "finger{i}.R_01", "thumb.R_01")
forearm = (wrist - arm.data.bones["lower_arm.R"].head_local).normalized()
# Neutral wrist at rest: the hand continues the forearm axis, so the cuff sits coaxially on the forearm; the palm keeps the baseline facing.
palmar = (palmar_base - forearm * palmar_base.dot(forearm)).normalized()
radial = forearm.cross(palmar).normalized()
basis0 = Matrix((radial0, along0, palmar0)).transposed()
basis1 = Matrix((radial, forearm, palmar)).transposed()
rotation = basis1 @ basis0.inverted()
REG = Matrix.Translation(wrist) @ rotation.to_4x4() @ Matrix.Translation(-wrist0)
assert abs(rotation.determinant() - 1) < 1e-6

# ---- reference copies of the protected r010 data, read before anything is edited ----
group_names0 = [g.name for g in hand.vertex_groups]
reference = {
    "points": [v.co.copy() for v in hand.data.vertices],
    "key_delta": [(hand.data.shape_keys.key_blocks[1].data[i].co - hand.data.shape_keys.key_blocks[0].data[i].co).length for i in range(len(hand.data.vertices))],
    "weights": [{group_names0[g.group]: g.weight for g in v.groups if g.weight > 0} for v in hand.data.vertices],
    "uv": [tuple(l.uv) for l in hand.data.uv_layers[0].data],
    "polygons": [tuple(p.vertices) for p in hand.data.polygons],
    "edges": [tuple(e.vertices) for e in hand.data.edges],
}
axial0 = [(p - wrist0).dot(along0) for p in reference["points"]]


def target_name(name, side="R"):
    if name in ("sword",):
        return name
    if name == "hand":
        return f"hand.{side}"
    stem, index = name.rsplit("_", 1)
    return f"{stem}.{side}_{index}"


# ---- bones ----
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
# wrist_transition follows the forearm exactly; it carries the cuff so the cuff stays part of the hand region.
for side, suffix in (("R", ""), ("L", ""), ("R", "_twist"), ("L", "_twist")):
    carrier = eb.get(f"wrist_transition.{side}{suffix}") or eb.new(f"wrist_transition.{side}{suffix}")
    forearm_bone = eb[f"lower_arm.{side}"]
    carrier.use_connect = False
    carrier.head = forearm_bone.tail.copy() if (forearm_bone.tail - eb[f"hand.{side}"].head).length < 1e-4 else eb[f"hand.{side}"].head.copy()
    carrier.tail = carrier.head - (carrier.head - forearm_bone.head).normalized() * 0.04
    carrier.roll = forearm_bone.roll
    carrier.parent = forearm_bone
    carrier.use_deform = True
order = ["hand"] + [f"finger{i}_0{j}" for i in (1, 2, 3, 4) for j in (1, 2, 3)] + ["thumb_01", "thumb_02", "thumb_03", "sword"]
bones_before = len(eb)
for name in order:
    src = hb[name]
    for side in ("R", "L"):
        if name == "sword" and side == "L":
            continue
        target = eb.get(target_name(name, side)) or eb.new(target_name(name, side))
        matrix = REG @ src.matrix_local
        if side == "L":
            # Mirror across X and flip the local X axis so the frame stays right-handed.
            matrix = MIRROR @ matrix @ MIRROR
        target.use_connect = False
        target.head = matrix.translation
        target.tail = matrix.translation + matrix.to_3x3().col[1] * src.length
        target.matrix = matrix
        target.length = src.length
        target.use_deform = True
        if name == "hand":
            target.parent = eb[f"lower_arm.{side}"]
        elif name == "sword":
            target.parent = eb["hand.R"]
        else:
            target.parent = eb[target_name(src.parent.name, side)]
bones_after = len(eb)
bpy.ops.object.mode_set(mode="OBJECT")

# ---- right hand mesh: rigid move only ----
hand.data.transform(REG, shape_keys=True)
hand.matrix_world = Matrix.Identity(4)
hand.name = "SM_RO_hand.R"
hand.data.name = "RO_hand_R"
collection.objects.link(hand)
hand.parent = arm
for modifier in hand.modifiers:
    if modifier.type == "ARMATURE":
        modifier.object = arm
for group in hand.vertex_groups:
    group.name = target_name(group.name)
points = [v.co.copy() for v in hand.data.vertices]
protected = {
    "vertices": len(points) == len(reference["points"]),
    "max_edge_length_change_m": max(abs((points[a] - points[b]).length - (reference["points"][a] - reference["points"][b]).length) for a, b in reference["edges"]),
    "polygons_identical": [tuple(p.vertices) for p in hand.data.polygons] == reference["polygons"],
    "uv_identical": [tuple(l.uv) for l in hand.data.uv_layers[0].data] == reference["uv"],
    "max_corrective_delta_change_m": max(abs((hand.data.shape_keys.key_blocks[1].data[i].co - hand.data.shape_keys.key_blocks[0].data[i].co).length - reference["key_delta"][i]) for i in range(len(points))),
}

# ---- weapon: same socket and placement the r010 grasp was verified with ----
sword = bpy.data.objects["SM_RO_sword"]
assert len(sword.data.vertices) == len(local_sword.data.vertices)
sample = range(0, len(sword.data.vertices) - 7, 97)
congruence = max(abs((sword.data.vertices[i].co - sword.data.vertices[i + 7].co).length - (local_sword.data.vertices[i].co - local_sword.data.vertices[i + 7].co).length) for i in sample)
assert congruence < 1e-5, congruence
sword_to_arm = REG @ local_sword.matrix_world
for v, w in zip(sword.data.vertices, local_sword.data.vertices):
    v.co = sword_to_arm @ w.co

# ---- remove what the new hand replaces; the forearm stump stops following the hand ----
replaced = {}
for name in ("SM_RO_glove.R", "SM_RO_WristLoft.R"):
    obj = bpy.data.objects[name]
    obj.data.calc_loop_triangles()
    replaced[name] = len(obj.data.loop_triangles)
    bpy.data.objects.remove(obj, do_unlink=True)
core = bpy.data.objects["SM_RO_core"]


def stump_to_forearm(side):
    """Core vertices lose every hand-side influence to the forearm bone; returns how many changed."""
    forearm_group = core.vertex_groups[f"lower_arm.{side}"]
    hand_groups = [g for g in core.vertex_groups if g.name.endswith(f".{side}") and g.name.startswith("hand") or f".{side}_" in g.name]
    changed = 0
    for v in core.data.vertices:
        moved = sum(g.weight for g in v.groups if core.vertex_groups[g.group] in hand_groups)
        if moved > 0:
            for group in hand_groups:
                group.remove([v.index])
            forearm_group.add([v.index], moved, "ADD")
            changed += 1
    for group in hand_groups:
        core.vertex_groups.remove(group)
    return changed


stump_right = stump_to_forearm("R")


def cut_stump(side, station):
    """Remove core geometry of one arm beyond a plane across the forearm; returns faces removed."""
    wrist_point = arm.data.bones[f"hand.{side}"].head_local.copy()
    axis = (wrist_point - arm.data.bones[f"lower_arm.{side}"].head_local).normalized()
    mesh = bmesh.new()
    mesh.from_mesh(core.data)
    layer = mesh.verts.layers.deform.verify()
    wanted_groups = {i for i, g in enumerate(core.vertex_groups) if g.name == f"lower_arm.{side}" or g.name.startswith(f"hand.{side}") or f".{side}_" in g.name}
    region = {v for v in mesh.verts if any(i in wanted_groups and w > 0 for i, w in v[layer].items()) and (v.co - wrist_point).dot(axis) > station - 0.08}
    before = len(mesh.faces)
    geometry = list(region) + [e for e in mesh.edges if e.verts[0] in region and e.verts[1] in region] + [f for f in mesh.faces if all(v in region for v in f.verts)]
    bmesh.ops.bisect_plane(mesh, geom=geometry, dist=1e-6, plane_co=wrist_point + axis * station, plane_no=axis, clear_outer=True, clear_inner=False)
    after = len(mesh.faces)
    mesh.to_mesh(core.data)
    mesh.free()
    core.data.update()
    return before - after

# ---- left: cut the old hand off the core where the right side was cut, mirror the bracer and the hand ----
bones = arm.data.bones
wrist_left = bones["hand.L"].head_local.copy()
forearm_left = (wrist_left - bones["lower_arm.L"].head_local).normalized()
station = args.stump_cut_mm / 1000
left_core = {"cut_axial_from_wrist_mm": args.stump_cut_mm, "faces_removed_left": cut_stump("L", station), "faces_removed_right": cut_stump("R", station)}
left_core["stump_vertices_reweighted"] = stump_to_forearm("L")
leftover = [v.index for v in core.data.vertices if (v.co - wrist_left).dot(forearm_left) > station + 1e-4 and (v.co - wrist_left).length < 0.3]
left_core["vertices_left_beyond_cut"] = len(leftover)

bracer_right, bracer_left = bpy.data.objects["SM_RO_bracer.R"], bpy.data.objects["SM_RO_bracer.L"]
assert [g.name for g in bracer_left.vertex_groups] == ["lower_arm.L"] and [g.name for g in bracer_right.vertex_groups] == ["lower_arm.R"]
if args.left_bracer == "mirror":
    old_bracer = bracer_left.data
    bracer_left.data = bracer_right.data.copy()
    bracer_left.data.name = "RO_bracer_L_mirrored"
    bracer_left.data.transform(MIRROR)
    bracer_left.data.flip_normals()
    bpy.data.meshes.remove(old_bracer)
    for group in bracer_left.vertex_groups:
        group.name = group.name.replace(".R", ".L")
    left_bracer = "mirror of the cut right bracer"
else:
    # Keep the left bracer's own shape and end it where the right one ends.
    right_end = max((v.co - bones["hand.R"].head_local).dot((bones["hand.R"].head_local - bones["lower_arm.R"].head_local).normalized()) for v in bracer_right.data.vertices)
    bracer_mesh = bmesh.new()
    bracer_mesh.from_mesh(bracer_left.data)
    faces_before_cut = len(bracer_mesh.faces)
    bmesh.ops.bisect_plane(bracer_mesh, geom=list(bracer_mesh.verts) + list(bracer_mesh.edges) + list(bracer_mesh.faces), dist=1e-6,
                           plane_co=wrist_left + forearm_left * right_end, plane_no=forearm_left, clear_outer=True, clear_inner=False)
    left_bracer = f"original left bracer cut at {right_end * 1e3:.1f} mm from the wrist; faces {faces_before_cut} -> {len(bracer_mesh.faces)}"
    bracer_mesh.to_mesh(bracer_left.data)
    bracer_mesh.free()
    bracer_left.data.update()
assert [g.name for g in bracer_left.vertex_groups] == ["lower_arm.L"]

left = bpy.data.objects.new("SM_RO_hand.L", hand.data.copy())
left.data.name = "RO_hand_L"
left.data.transform(MIRROR, shape_keys=True)
left.data.flip_normals()
collection.objects.link(left)
left.parent = arm
# Vertex groups live on the mesh data, so the copy arrives with the right-side names: rename, do not add.
for group in left.vertex_groups:
    group.name = group.name.replace(".R", ".L")
assert len(left.vertex_groups) == len(hand.vertex_groups) and all(".R" not in g.name for g in left.vertex_groups)
left.modifiers.new("Skin", "ARMATURE").object = arm

# ---- local weight smoothing on the core where single triangles fold under shoulder and spine motion ----
relax = {"applied": False}
if args.relax_core:
    centres = [Vector(tuple(float(c) for c in item.split(","))) for item in args.relax_core.split(";")]
    radius = args.relax_radius_mm / 1000
    neighbours = {v.index: set() for v in core.data.vertices}
    for edge in core.data.edges:
        a, b = edge.vertices
        neighbours[a].add(b)
        neighbours[b].add(a)
    group_count = len(core.vertex_groups)
    weights = [[0.0] * group_count for _ in core.data.vertices]
    for v in core.data.vertices:
        for g in v.groups:
            weights[v.index][g.group] = g.weight
    region = sorted(v.index for v in core.data.vertices if any((v.co - c).length < radius for c in centres))
    for _ in range(8):
        updated = {}
        for index in region:
            ring = neighbours[index]
            if ring:
                mean = [sum(weights[n][g] for n in ring) / len(ring) for g in range(group_count)]
                updated[index] = [0.5 * weights[index][g] + 0.5 * mean[g] for g in range(group_count)]
        for index, row in updated.items():
            weights[index] = row
    for index in region:
        top = sorted(range(group_count), key=lambda g: -weights[index][g])[:4]
        total = sum(weights[index][g] for g in top)
        for g in range(group_count):
            if g in top and weights[index][g] / total > 1e-4:
                core.vertex_groups[g].add([index], weights[index][g] / total, "REPLACE")
            else:
                core.vertex_groups[g].remove([index])
    relax = {"applied": True, "centres": [[round(c, 4) for c in centre] for centre in centres], "radius_mm": args.relax_radius_mm, "vertices": len(region), "iterations": 8}

# ---- single folding triangles: give the three vertices one weight set so the triangle moves as a piece ----
rigid = {"applied": False}
if args.rigid_core:
    core.data.calc_loop_triangles()
    group_count = len(core.vertex_groups)
    sites = []
    for item in args.rigid_core.split(";"):
        centre = Vector(tuple(float(c) for c in item.split(",")))
        triangle = min(core.data.loop_triangles, key=lambda t: (t.center - centre).length)
        if (triangle.center - centre).length > 0.003:
            raise SystemExit(f"RIGID_CORE_TRIANGLE_NOT_FOUND {item}")
        mean = [0.0] * group_count
        for index in triangle.vertices:
            for g in core.data.vertices[index].groups:
                mean[g.group] += g.weight / 3
        top = sorted(range(group_count), key=lambda g: -mean[g])[:4]
        total = sum(mean[g] for g in top)
        for index in triangle.vertices:
            for g in range(group_count):
                if g in top and mean[g] / total > 1e-4:
                    core.vertex_groups[g].add([index], mean[g] / total, "REPLACE")
                else:
                    core.vertex_groups[g].remove([index])
        sites.append({"centre": [round(c, 4) for c in centre], "vertices": list(triangle.vertices)})
    rigid = {"applied": True, "sites": sites}

# ---- toes: the front of each boot follows the toe bone (core weights are not protected) ----
toes = {"applied": False}
if args.toe_blend_mm is not None:
    span = args.toe_blend_mm / 1000
    toes = {"applied": True, "blend_mm": args.toe_blend_mm, "radius_mm": args.toe_radius_mm}
    for side in ("R", "L"):
        toe_bone, foot_group = arm.data.bones[f"toe.{side}"], core.vertex_groups[f"foot.{side}"]
        toe_group = core.vertex_groups.get(f"toe.{side}") or core.vertex_groups.new(name=f"toe.{side}")
        direction = (toe_bone.tail_local - toe_bone.head_local).normalized()
        count = 0
        for v in core.data.vertices:
            foot_weight = sum(g.weight for g in v.groups if g.group == foot_group.index)
            ahead = (v.co - toe_bone.head_local).dot(direction)
            offset = v.co - toe_bone.head_local
            beside = (offset - direction * offset.dot(direction)).length
            side = min(1.0, max(0.0, (beside - args.toe_radius_mm / 1000) / 0.035))
            sideways = 1.0 - side * side * (3 - 2 * side)
            if foot_weight > 0 and ahead > -span / 2 and sideways > 0:
                t = min(1.0, (ahead + span / 2) / span)
                share = foot_weight * t * t * (3 - 2 * t) * sideways
                foot_group.add([v.index], foot_weight - share, "REPLACE")
                toe_group.add([v.index], share, "REPLACE")
                count += 1
        toes[f"vertices_{side}"] = count

# ---- optional, authorization-gated: cuff follows the forearm ----
cuff = {"applied": False, "vertices_behind_wrist": sum(1 for a in axial0 if a < 0)}
if args.cuff_blend_mm is not None:
    span = args.cuff_blend_mm / 1000
    changed = []
    for obj, side in ((hand, "R"), (left, "L")):
        hand_group = obj.vertex_groups[f"hand.{side}"]
        forearm_group = obj.vertex_groups.get(f"wrist_transition.{side}") or obj.vertex_groups.new(name=f"wrist_transition.{side}")
        twist_group = obj.vertex_groups.get(f"wrist_transition.{side}_twist") or obj.vertex_groups.new(name=f"wrist_transition.{side}_twist")
        for index, axial in enumerate(axial0):
            if axial < 0:
                t = max(0.0, 1.0 + axial / span)
                keep = t * t * (3 - 2 * t)
                # Beyond the hand blend the cuff belongs to the twist carrier, fading to the static carrier over --twist-fade-mm further back.
                u = min(1.0, max(0.0, (axial + span) / (args.twist_fade_mm / 1000) + 1.0))
                turning = u * u * (3 - 2 * u)
                for group, weight in ((hand_group, keep), (twist_group, (1 - keep) * turning), (forearm_group, (1 - keep) * (1 - turning))):
                    if weight > 1e-6:
                        group.add([index], weight, "REPLACE")
                    else:
                        group.remove([index])
                if side == "R":
                    changed.append(index)
    cuff.update({"applied": True, "blend_mm": args.cuff_blend_mm, "right_vertex_ids_changed": changed})
names_now = [g.name for g in hand.vertex_groups]
weights_now = [{names_now[g.group]: g.weight for g in v.groups if g.weight > 0} for v in hand.data.vertices]
protected["weights_identical_ids"] = sum(1 for now, before in zip(weights_now, reference["weights"]) if now == {target_name(k): w for k, w in before.items()})
protected["weights_changed_ids"] = len(points) - protected["weights_identical_ids"]

# ---- pose and rule data that travel with the hand ----
grasp = {}
for name in order:
    if name in ("hand", "sword"):
        continue
    curves = [grasp_action.fcurves.find(f'pose.bones["{name}"].rotation_quaternion', index=i) for i in range(4)]
    quaternion = [c.evaluate(61) for c in curves]
    grasp[name] = quaternion
poses = {"grasp.R": {target_name(n, "R"): q for n, q in grasp.items()},
         "grasp.L": {target_name(n, "L"): [q[0], q[1], -q[2], -q[3]] for n, q in grasp.items()},
         "source": "r010 AN_RO_RightHand_GraspDiagnostic frame 61, finger and thumb bones only; left is the mirror image"}
rules = {"schema_version": 1, "id": f"ro-swordsman-character-v1-v001-{args.tag}", "status": "candidate",
         "quaternion_convention": "wxyz; rest-relative local rotation of the bone",
         "drivers": {"grasp.R": {"type": "state", "key": "grasp.R"}, "grasp.L": {"type": "state", "key": "grasp.L"}},
         "channels": [{"mesh": f"SM_RO_hand.{side}", "morph": "SK_RO_GraspPulp_Corrective", "owner": "runtime_evaluator", "kind": "contact_state",
                       "driver": f"grasp.{side}", "curve": {"type": "linear"}} for side in ("R", "L")]}
(OUT / "poses.json").write_text(json.dumps(poses, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
(OUT / "corrective-rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))

materials_note = "Both hands still carry the r010 gray review material."
if args.hand_material:
    material_source = ROOT / "assets/processed/ro-swordsman-combo-r007/v004-root-weights/right_hand_root_weights.blend"
    with bpy.data.libraries.load(str(material_source), link=False) as (available_materials, wanted_materials):
        wanted_materials.materials = ["M_RO_Hand_SourcePBR_Explicit"]
    leather = wanted_materials.materials[0]
    leather.name = "M_RO_Hand_Leather"
    for obj in (hand, left):
        obj.data.materials.clear()
        obj.data.materials.append(leather)
    materials_note = ("Both hands use the r007 source PBR material (diffuse, metallic, roughness, normal, 2048 px, packed). The 16 faces of the thumb patch that "
                      "sample across UV islands are still unresolved, and the left hand shows the mirrored texture.")

for leftover_object in (hand_arm, local_sword):
    bpy.data.objects.remove(leftover_object, do_unlink=True)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
bpy.context.view_layer.update()
triangles = {}
for obj in sorted((o for o in arm.children if o.type == "MESH"), key=lambda o: o.name):
    obj.data.calc_loop_triangles()
    triangles[obj.name] = len(obj.data.loop_triangles)
blend = OUT / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "tag": args.tag,
    "sources": {"whole": source, "whole_sha256_after": sha(ROOT / source["path"]), "hand": {"path": HAND_BLEND.relative_to(ROOT).as_posix(), "sha256": sha(HAND_BLEND)}},
    "output": {"path": blend.relative_to(ROOT).as_posix(), "sha256": sha(blend), "bytes": blend.stat().st_size},
    "registration": {"rule": "wrist joint to wrist joint; hand axis on the forearm axis; palm facing as in the baseline; rigid, no scale",
                     "matrix_rows": [[round(c, 8) for c in row] for row in REG], "determinant": rotation.determinant()},
    "bones": {"before": bones_before, "after": bones_after, "cuff_carriers": ["wrist_transition.R", "wrist_transition.L", "wrist_transition.R_twist", "wrist_transition.L_twist"], "right_hand_frames": "r010 bone matrices under the registration", "left_hand_frames": "mirror of the right"},
    "protected_r010_hand": protected, "cuff": cuff, "toes": toes, "weapon": {"congruence_max_m": congruence, "socket": "r010 sword bone under the registration"},
    "replaced_right_parts_triangles": replaced, "core_right_stump_vertices_reweighted": stump_right, "left_core": left_core,
    "left_bracer": left_bracer, "core_relax": relax, "core_rigid_triangles": rigid, "triangles": triangles, "triangles_total": sum(triangles.values()), "triangle_budget": 60000,
    "materials_note": materials_note,
}
(QA / "assemble-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_V001_ASSEMBLE", json.dumps({"bones": [bones_before, bones_after], "triangles_total": report["triangles_total"], "protected": protected, "left_core": left_core, "cuff": {k: v for k, v in cuff.items() if k != "right_vertex_ids_changed"}}))
