"""Diagnostic (report only) for LieDown a02:
(1) release direction: at the put-down pose (clip frame 34: fingers open, hand on the bed socket grip), move the hand IK target
    by 2, 5 and 10 cm along candidate directions and count SM_RO_hand.R x SM_RO_sword overlapping triangle pairs;
(2) sword-body crossings at the failing times: meshes, dominant bones and the crossing region."""
import json, math, sys, collections
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
from cv1_arm_ik import ArmIK
config = interaction.load(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_LieDown/interaction.json")
spec = json.loads((ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_LieDown/a02/clip-spec.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(str(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_LieDown/a02/AN_RO_LieDown.blend"), link=False) as (s, d):
    d.actions = ["AN_RO_LieDown"]
act = bpy.data.actions["AN_RO_LieDown"]
arm.animation_data_create(); arm.animation_data.action = act
sock = config["sword_socket"]["bed_socket"]
SOCKET = Matrix.Translation(Vector(sock["head_m"])) @ Quaternion(sock["quaternion_wxyz"]).to_matrix().to_4x4()
P = arm.pose.bones
def mesh_tree(name):
    dg = bpy.context.evaluated_depsgraph_get(); ev = bpy.data.objects[name].evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    pts = [ev.matrix_world @ v.co for v in m.vertices]; tris = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
    return pts, tris, BVHTree.FromPolygons(pts, tris)
def place(t):
    f = math.floor(t); bpy.context.scene.frame_set(f, subframe=t - f)
    if interaction.socket_at(config, t) == "bed":
        P["sword"].matrix = arm.matrix_world.inverted() @ SOCKET
    bpy.context.view_layer.update()
out = {"release": [], "crossings": []}
# (1) release directions at frame 34 (keyed pose), then the action is detached so the IK can move the arm
place(34)
hand0 = P["hand.R"].matrix.copy()
pose34 = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in P}
arm.animation_data.action = None
ik = ArmIK(arm)
swivel = -40.0
sw_pts, sw_tris, sw_tree = mesh_tree("SM_RO_sword")
dirs = {"+z": (0, 0, 1), "+z+y": (0, 0.5, 0.87), "+z-y": (0, -0.5, 0.87), "+z+x": (0.5, 0, 0.87), "+z-x": (-0.5, 0, 0.87), "+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0),
        "-x": (-1, 0, 0), "palm_out": None, "back_along_forearm": None}
forearm = (P["hand.R"].head - P["lower_arm.R"].head).normalized()
palm_normal = (hand0.to_3x3() @ Vector((0, 0, 1))).normalized()
dirs["palm_out(+Zbone)"] = tuple(palm_normal); dirs["palm_in(-Zbone)"] = tuple(-palm_normal); dirs["back_along_forearm"] = tuple(-forearm)
dirs["hand_x"] = tuple((hand0.to_3x3() @ Vector((1, 0, 0))).normalized()); dirs["hand_-x"] = tuple(-(hand0.to_3x3() @ Vector((1, 0, 0))).normalized())
for name, d in dirs.items():
    if d is None:
        continue
    counts = []
    for dist in (0.02, 0.05, 0.10):
        for pb in P:
            pb.location, pb.rotation_quaternion = pose34[pb.name]
        bpy.context.view_layer.update()
        P["sword"].matrix = arm.matrix_world.inverted() @ SOCKET
        bpy.context.view_layer.update()
        target = Matrix.Translation(Vector(d) * dist) @ hand0
        try:
            ik.solve("R", target, swivel)
            P["sword"].matrix = arm.matrix_world.inverted() @ SOCKET
            bpy.context.view_layer.update()
            hp, ht, htree = mesh_tree("SM_RO_hand.R")
            counts.append(len(htree.overlap(sw_tree)))
        except ValueError:
            counts.append("reach")
    out["release"].append({"direction": name, "vector": [round(c, 3) for c in d], "pairs_at_2_5_10cm": counts})
    print("REL %-22s %s pairs at 2/5/10 cm: %s" % (name, [round(c, 2) for c in d], counts))
# (2) crossings at failing times
arm.animation_data.action = act
for t in (46.5, 48.5, 50.0, 51.5, 52.0, 57.5, 58.0, 59.0):
    place(t)
    sp, st, stree = mesh_tree("SM_RO_sword")
    hits = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name != "SM_RO_sword" and any(m.type == "ARMATURE" for m in obj.modifiers):
            bp, bt, btree = mesh_tree(obj.name); pairs = stree.overlap(btree)
            if pairs:
                names = [g.name for g in obj.vertex_groups]
                dom = collections.Counter(max(((names[g.group], g.weight) for g in obj.data.vertices[bt[j][0]].groups), key=lambda x: x[1], default=("?", 0))[0] for _, j in pairs)
                cen = [sum((bp[i] for i in bt[j]), Vector()) / 3 for _, j in pairs]
                hits[obj.name] = {"pairs": len(pairs), "bones": dict(dom.most_common(3)), "x": [round(min(c.x for c in cen), 3), round(max(c.x for c in cen), 3)],
                                  "y": [round(min(c.y for c in cen), 3), round(max(c.y for c in cen), 3)], "z": [round(min(c.z for c in cen), 3), round(max(c.z for c in cen), 3)]}
    out["crossings"].append({"t": t, "pelvis_head": [round(c, 3) for c in P["pelvis"].head], "hits": hits})
    print("CROSS t %s pelvis %s %s" % (t, [round(c, 3) for c in P["pelvis"].head], json.dumps(hits)))
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
