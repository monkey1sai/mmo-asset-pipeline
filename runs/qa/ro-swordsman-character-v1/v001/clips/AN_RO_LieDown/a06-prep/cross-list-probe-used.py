"""Design probe (report only): sword-body crossings by body part, and body points sunk into the bed, along a clip.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python clearance-probe-used.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --rules <rules.json> --contract <contract.json> \
       --times a:b:step[,a:b:step] --out <report.json>
Each time is evaluated the way scripts/cv1_clip_check.py evaluates it (action, bed socket after the event, helpers,
interaction states, correctives). Measured: the clip check's sword-against-non-hand crossing (pairs, depth) with the
meshes and dominant bones of the crossing body triangles; the closest body point to the sword surface per body part;
the deepest body point below the bed top while over the bed footprint, with its dominant bone, and per mesh and
dominant bone the count and depth of such points. Not a gate.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_soup import Soup

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--rules", "--contract", "--times", "--out"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
config = interaction.load(ROOT / args.interaction)
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
limits = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))["limits"]
times = []
for part in args.times.split(","):
    a, b, step = (float(x) for x in part.split(":"))
    times += [a + i * step for i in range(int(round((b - a) / step)) + 1)]

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (source, target):
    target.actions = [config["clip"]]
action = bpy.data.actions[config["clip"]]
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
sword_obj = bpy.data.objects["SM_RO_sword"]
SOCKET = config.get("sword_socket")
BED_SOCKET = (Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()) if SOCKET else None
bed = config.get("bed")


def zero_keys():
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0


arm.animation_data_create()
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
zero_keys()
bpy.context.view_layer.update()
soup = Soup(meshes, limits)
soup.set_rest()
arm.animation_data.action = action
mesh_of_point = []
for obj in meshes:
    mesh_of_point += [obj.name] * len(obj.data.vertices)


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def evaluate(t):
    frame = math.floor(t)
    scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    if SOCKET and interaction.socket_at(config, t) == "bed":
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ BED_SOCKET
        bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    states = interaction.states_at(config, t)
    state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
    zero_keys()
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()


def crossing(tri, plane):
    normal = (plane[1] - plane[0]).cross(plane[2] - plane[0])
    if normal.length < 1e-14:
        return 0.0
    normal.normalize()
    side = [(p - plane[0]).dot(normal) for p in tri]
    return min(max(0.0, max(side)), max(0.0, -min(side)))


def part_of(bone):
    if bone in ("coat.L", "coat.R", "tabard"):
        return bone  # the two half-skirts and the front panel apart
    for prefix, part in (("upper_leg", "thigh"), ("lower_leg", "shin"), ("foot", "foot"), ("toe", "foot"), ("coat", "coat"),
                         ("pelvis", "pelvis"), ("spine", "torso"), ("hand", "hand"), ("finger", "hand"), ("thumb", "hand"),
                         ("lower_arm", "forearm"), ("upper_arm", "upper_arm"), ("wrist", "hand")):
        if bone.startswith(prefix):
            return part
    return "other"


rows = []
for t in times:
    evaluate(t)
    points = soup.evaluated_points()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = sword_obj.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    mesh.calc_loop_triangles()
    sword_points = [target.matrix_world @ v.co for v in mesh.vertices]
    sword_tris = [tuple(tri.vertices) for tri in mesh.loop_triangles]
    target.to_mesh_clear()
    sword_tree = BVHTree.FromPolygons(sword_points, sword_tris, all_triangles=True)
    soup_tree = BVHTree.FromPolygons(points, soup.tris, all_triangles=True)
    depth, by_part = 0.0, {}
    for i, j in sword_tree.overlap(soup_tree):
        if soup.tri_hand[j]:
            continue
        d = min(crossing([sword_points[k] for k in sword_tris[i]], [points[k] for k in soup.tris[j]]),
                crossing([points[k] for k in soup.tris[j]], [sword_points[k] for k in sword_tris[i]]))
        depth = max(depth, d)
        if d > 0.001:
            rest_centre = sum((soup.rest[k] for k in soup.tris[j]), Vector()) / 3
            print("CV1_CROSS " + json.dumps({"t": t, "mesh": soup.tri_mesh[j], "dominant": soup.dominant[soup.tris[j][0]], "depth_mm": round(d * 1e3, 2),
                                              "rest_centre_m": [round(c, 3) for c in rest_centre], "sword_tri_centre_m": [round(c, 3) for c in sum((sword_points[k] for k in sword_tris[i]), Vector()) / 3]}))
        key = f"{soup.tri_mesh[j]}:{part_of(soup.dominant[soup.tris[j][0]])}"
        by_part[key] = max(by_part.get(key, 0.0), d)
    nearest = {}
    for idx, p in enumerate(points):
        found = sword_tree.find_nearest(p, 0.06)
        if found[0] is None:
            continue
        part = part_of(soup.dominant[idx])
        if part == "hand":
            continue
        signed = (p - found[0]).dot(found[1])
        if part not in nearest or signed < nearest[part][0]:
            nearest[part] = (signed, mesh_of_point[idx])
    sink, sunk = None, {}
    if bed:
        cx, cy = bed["centre_m"]
        half_l, half_w = bed["size_m"][0] / 2, bed["size_m"][1] / 2
        yaw = math.radians(bed["yaw_deg"])
        for idx, p in enumerate(points):
            dx, dy = p.x - cx, p.y - cy
            u, v = dx * math.cos(yaw) + dy * math.sin(yaw), -dx * math.sin(yaw) + dy * math.cos(yaw)
            if abs(u) <= half_l and abs(v) <= half_w and p.z < bed["top_z_m"]:
                d = bed["top_z_m"] - p.z
                if sink is None or d > sink[0]:
                    sink = (d, soup.dominant[idx], mesh_of_point[idx], [round(c, 3) for c in p])
                group = sunk.setdefault(f"{mesh_of_point[idx]}:{soup.dominant[idx]}", [0, 0.0])
                group[0] += 1
                group[1] = max(group[1], d)
    row = {"t": t, "weapon_body_depth_mm": round(depth * 1e3, 2), "weapon_body_by_part_mm": {k: round(v * 1e3, 2) for k, v in sorted(by_part.items())},
           "nearest_signed_mm": {k: [round(v[0] * 1e3, 1), v[1]] for k, v in sorted(nearest.items())},
           "bed_sink_mm": None if sink is None else [round(sink[0] * 1e3, 1), sink[1], sink[2], sink[3]],
           "bed_sunk_points": {k: [v[0], round(v[1] * 1e3, 1)] for k, v in sorted(sunk.items())}}
    rows.append(row)
    print("CV1_CLEARANCE " + json.dumps(row))
Path(args.out).write_text(json.dumps({"clip_blend": args.clip_blend, "interaction": args.interaction, "rows": rows}, indent=1) + "\n", encoding="utf-8", newline="\n")
