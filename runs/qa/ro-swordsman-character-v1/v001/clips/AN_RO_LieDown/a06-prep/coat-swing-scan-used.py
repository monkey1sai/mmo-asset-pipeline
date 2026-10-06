"""Probe (report only): coat-bone rotation candidates at chosen clip times. For each time and candidate, coat.L / coat.R
are set to the candidate's contract steps from their rest rotation (replacing the clip's coat keys), then the clip is
evaluated as scripts/cv1_clip_check.py does (bed socket, helpers, interaction states, correctives) and measured:
coat triangle collapse (contract collapse ratio) and fold-through (scripts/cv1_soup.py flip diagnostic), and the sword
crossing depth against the non-hand body triangles (the clip check's weapon_body crossing measure), per mesh and
dominant bones of the crossing body triangle, and the deepest non-hand point below the bed top over the (yaw 0) bed
footprint, coat and other apart. Nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-swing-scan-used.py -- \
       <action .blend> <interaction.json> <rules.json> <contract.json> <times comma list> <candidates.json> <out.json>
candidates.json: {"name": {"coat.L": [["in", 15]], "coat.R": [["in", 15]]}, ...}  (toward, degrees; contract swing, or
["about:left", degrees] for a contract twist about that fixed rest axis)
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser
from cv1_soup import Soup, tri_area

action_blend, interaction_path, rules_path, contract_path, times, candidates_path, out = sys.argv[sys.argv.index("--") + 1:]
config = interaction.load(Path(interaction_path))
rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
candidates = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
limits = contract["limits"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
poser = ContractPoser(arm, contract, {})
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
SOCKET = config.get("sword_socket")
BED_SOCKET = Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()
sword_obj = bpy.data.objects["SM_RO_sword"]


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


def evaluate_at(t, coat_steps):
    frame = math.floor(t)
    bpy.context.scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    for name in ("coat.L", "coat.R"):
        q = Quaternion()
        for toward, degrees in coat_steps.get(name, []):
            # "about:<axis>" = contract twist about a fixed rest axis (the same rotation for both coat bones)
            step = {"bone": name, "kind": "twist", "about": toward[6:], "degrees": degrees} if toward.startswith("about:") else                 {"bone": name, "kind": "swing", "toward": toward, "degrees": degrees}
            q = q @ poser.step_rotation(step, name[-1], 1.0)
        arm.pose.bones[name].rotation_quaternion = q
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


def crossing(tri, plane):
    normal = (plane[1] - plane[0]).cross(plane[2] - plane[0])
    if normal.length < 1e-14:
        return 0.0
    normal.normalize()
    side = [(p - plane[0]).dot(normal) for p in tri]
    return min(max(0.0, max(side)), max(0.0, -min(side)))


reset_pose()
soup = Soup(meshes, limits)
soup.set_rest()
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [config["clip"]]
coat_tris = [i for i, m in enumerate(soup.tri_mesh) if m == "SM_RO_coat"]
point_mesh = [name for obj in meshes for name in [obj.name] * len(obj.data.vertices)]  # yaw-0 bed proxy assumed below
coat_set = set(coat_tris)
rows = []
for t in [float(x) for x in times.split(",")]:
    for name, steps in candidates.items():
        arm.animation_data.action = dst.actions[0]
        evaluate_at(t, steps)
        points = soup.evaluated_points()
        agreement = soup.normal_agreement(points)
        ratios = {i: tri_area(points, soup.tris[i]) / soup.rest_area[i] for i in coat_tris if soup.rest_area[i] > limits["min_rest_triangle_area_m2"]}
        collapsed = sorted(i for i, r in ratios.items() if r < limits["collapse_area_ratio"])
        flipped = sorted(i for i in coat_tris if agreement[i] is not None and soup.rest_agreement[i] is not None and soup.rest_agreement[i] > 0.5 and agreement[i] < 0.0)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        target = sword_obj.evaluated_get(depsgraph)
        mesh = target.to_mesh()
        mesh.calc_loop_triangles()
        sword_points = [target.matrix_world @ v.co for v in mesh.vertices]
        sword_tris = [tuple(lt.vertices) for lt in mesh.loop_triangles]
        target.to_mesh_clear()
        sword_tree = BVHTree.FromPolygons(sword_points, sword_tris, all_triangles=True)
        soup_tree = BVHTree.FromPolygons(points, soup.tris, all_triangles=True)
        by_bone, deepest = {}, (0.0, None, None)
        for i, j in sword_tree.overlap(soup_tree):
            if soup.tri_hand[j]:
                continue
            a = [sword_points[k] for k in sword_tris[i]]
            b = [points[k] for k in soup.tris[j]]
            depth = min(crossing(a, b), crossing(b, a))
            bone = soup.tri_mesh[j][6:] + ":" + "+".join(sorted({soup.dominant[k] for k in soup.tris[j]}))
            by_bone[bone] = max(by_bone.get(bone, 0.0), depth)
            if depth > deepest[0]:
                deepest = (depth, [round(c, 3) for c in sum(a, Vector()) / 3], [round(c, 3) for c in soup.centre(soup.rest, j)])
        bed = config["bed"]
        cx, cy = bed["centre_m"]
        half_l, half_w, top = bed["size_m"][0] / 2, bed["size_m"][1] / 2, bed["top_z_m"]
        depth = {"coat": 0.0, "other": 0.0}
        for k, p in enumerate(points):
            if p.z < top and abs(p.x - cx) <= half_l and abs(p.y - cy) <= half_w and not soup.is_hand_vertex[k]:
                kind = "coat" if point_mesh[k] == "SM_RO_coat" else "other"
                depth[kind] = max(depth[kind], top - p.z)
        row = {"t": t, "candidate": name, "coat_min_ratio": round(min(ratios.values()), 4), "collapsed": collapsed, "flipped": len(flipped),
               "bed_depth_mm": {k: round(v * 1e3, 1) for k, v in depth.items()},
               "sword_crossing_mm": {k: round(v * 1e3, 2) for k, v in sorted(by_bone.items(), key=lambda kv: -kv[1]) if v > 0.0},
               "deepest_crossing": {"sword_at": deepest[1], "coat_rest_at": deepest[2]} if deepest[1] else None}
        rows.append(row)
        print("CV1_SWING " + json.dumps({k: (v if k != "collapsed" else len(v)) for k, v in row.items()}))
reset_pose()
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
