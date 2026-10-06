"""Probe (report only): which coat triangles collapse (area ratio < the contract's collapse ratio) or fold through (the
scripts/cv1_soup.py flip diagnostic: facing against neighbours they agreed with at rest) at chosen clip times, and which
factor makes them: the clip as authored, the 'lying' state forced to 0 (b20 coat lying corrective off), the coat tuck
removed (coat.L / coat.R back to rest rotation; the clip keys only the 'in' swing on them), or both.
Evaluation as scripts/cv1_clip_check.py (action, bed socket, helpers, interaction states, correctives). Nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-fold-probe-used.py -- \
       <action .blend> <interaction.json> <rules.json> <contract.json> <times comma list> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_soup import Soup, tri_area

action_blend, interaction_path, rules_path, contract_path, times, out = sys.argv[sys.argv.index("--") + 1:]
config = interaction.load(Path(interaction_path))
rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
limits = contract["limits"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
SOCKET = config.get("sword_socket")
BED_SOCKET = Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()


def reset_pose():
    arm.animation_data_create()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0
    bpy.context.view_layer.update()


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def evaluate_at(t, lying=None, untuck=False):
    frame = math.floor(t)
    bpy.context.scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    if untuck:
        for name in ("coat.L", "coat.R"):
            arm.pose.bones[name].rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
    if interaction.socket_at(config, t) == "bed":
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ BED_SOCKET
        bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    states = interaction.states_at(config, t)
    state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
    if lying is not None:
        state["lying"] = lying
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    return state


reset_pose()
soup = Soup(meshes, limits)
soup.set_rest()
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [config["clip"]]
arm.animation_data.action = dst.actions[0]
coat_tris = [i for i, m in enumerate(soup.tri_mesh) if m == "SM_RO_coat"]
ratio_limit = limits["collapse_area_ratio"]
VARIANTS = {"as_authored": {}, "lying0": {"lying": 0.0}, "untucked": {"untuck": True}, "untucked_lying0": {"lying": 0.0, "untuck": True}}
rows = []
for t in [float(x) for x in times.split(",")]:
    row = {"t": t}
    for name, opts in VARIANTS.items():
        arm.animation_data.action = dst.actions[0]
        state = evaluate_at(t, **opts)
        points = soup.evaluated_points()
        agreement = soup.normal_agreement(points)
        collapsed = sorted(i for i in coat_tris if soup.rest_area[i] > limits["min_rest_triangle_area_m2"] and tri_area(points, soup.tris[i]) / soup.rest_area[i] < ratio_limit)
        flipped = sorted(i for i in coat_tris if agreement[i] is not None and soup.rest_agreement[i] is not None and soup.rest_agreement[i] > 0.5 and agreement[i] < 0.0)
        ratios = [tri_area(points, soup.tris[i]) / soup.rest_area[i] for i in coat_tris if soup.rest_area[i] > limits["min_rest_triangle_area_m2"]]
        row[name] = {"lying": round(state.get("lying", 0.0), 3), "coat_min_ratio": round(min(ratios), 4), "collapsed": collapsed, "flipped": flipped}
    rows.append(row)
    print("CV1_FOLD " + json.dumps({"t": t, **{k: (v["coat_min_ratio"], len(v["collapsed"]), len(v["flipped"])) for k, v in row.items() if k != "t"}}))
reset_pose()
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
