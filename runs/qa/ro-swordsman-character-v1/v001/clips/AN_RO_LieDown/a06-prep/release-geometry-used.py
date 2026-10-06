"""Probe (report only): right-hand geometry around the sword put-down. At each listed clip time, evaluated as
scripts/cv1_clip_check.py does (action, bed socket from the switch event, helpers, interaction states, correctives):
the hand frame in world space (along = wrist to the finger-base centre, palmar / dorsal / radial as in
scripts/cv1_contract_pose.py), the wrist point, the four finger-base points, the fingertip points (finger bone tails),
the sword grip axis (sword bone head and direction) and, for the SM_RO_hand.R mesh, the lowest point, the deepest
point inside a 15 mm grip cylinder and the bed-top depth. Nothing is saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python release-geometry-used.py -- \
       <action .blend> <interaction.json> <rules.json> <times comma list> <out.json>
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

action_blend, interaction_path, rules_path, times, out = sys.argv[sys.argv.index("--") + 1:]
config = interaction.load(Path(interaction_path))
rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [config["clip"]]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
SOCKET = config["sword_socket"]
BED_SOCKET = Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()
top = config["bed"]["top_z_m"]


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def evaluate_at(t):
    frame = math.floor(t)
    bpy.context.scene.frame_set(frame, subframe=t - frame)
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
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()


def world(name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def r(v, n=4):
    return [round(c, n) for c in v]


rows = []
hand_obj = bpy.data.objects["SM_RO_hand.R"]
for t in [float(x) for x in times.split(",")]:
    evaluate_at(t)
    wrist = world("hand.R")
    mcp = {i: world(f"finger{i}.R_01") for i in (1, 2, 3, 4)}
    thumb = world("thumb.R_01")
    index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
    along = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
    across = mcp[index] - mcp[pinky]
    radial = (across - along * across.dot(along)).normalized()
    palmar = radial.cross(along).normalized()
    tips = {}
    for i in (1, 2, 3, 4):
        last = max((b for b in arm.pose.bones if b.name.startswith(f"finger{i}.R_")), key=lambda b: b.name)
        tips[i] = world(last.name, tail=True)
    tips["thumb"] = world(max((b for b in arm.pose.bones if b.name.startswith("thumb.R_")), key=lambda b: b.name).name, tail=True)
    sword = arm.pose.bones["sword"]
    grip_head = arm.matrix_world @ sword.head
    grip_dir = ((arm.matrix_world @ sword.tail) - grip_head).normalized()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = hand_obj.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    pts = [target.matrix_world @ v.co for v in mesh.vertices]
    target.to_mesh_clear()
    lowest = min(pts, key=lambda p: p.z)
    # Distance of each hand point to the sword bone line (the grip lies along the bone near its head).
    def radial_distance(p):
        d = p - grip_head
        return (d - grip_dir * d.dot(grip_dir)).length, d.dot(grip_dir)
    inside = [(radial_distance(p), p) for p in pts]
    inside = [(rd, ax, p) for (rd, ax), p in inside if rd < 0.015 and -0.25 < ax < 0.25]
    rows.append({"t": t, "wrist": r(wrist), "along": r(along, 3), "palmar": r(palmar, 3), "radial": r(radial, 3),
                 "mcp": {i: r(p) for i, p in mcp.items()}, "tips": {str(k): r(p) for k, p in tips.items()},
                 "grip_head": r(grip_head), "grip_dir": r(grip_dir, 3), "hand_lowest": r(lowest), "hand_depth_below_top_mm": round((top - lowest.z) * 1e3, 1),
                 "hand_points_within_15mm_of_sword_axis": len(inside),
                 "deepest_inside": None if not inside else {"radial_mm": round(min(inside)[0] * 1e3, 1), "at": r(min(inside)[2]), "axial_m": round(min(inside)[1], 3)}})
    print("CV1_RELEASE " + json.dumps(rows[-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
