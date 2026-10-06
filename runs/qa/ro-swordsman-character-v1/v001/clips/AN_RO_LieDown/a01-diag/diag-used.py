"""Diagnostic (report only): LieDown a01 joint angles at sample times and the meshes the socketed sword crosses."""
import json, math, sys, collections
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
config = interaction.load(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_LieDown/interaction.json")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(str(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_LieDown/a01/AN_RO_LieDown.blend"), link=False) as (s, d):
    d.actions = ["AN_RO_LieDown"]
arm.animation_data_create(); arm.animation_data.action = bpy.data.actions["AN_RO_LieDown"]
sock = config["sword_socket"]["bed_socket"]
SOCKET = Matrix.Translation(Vector(sock["head_m"])) @ Quaternion(sock["quaternion_wxyz"]).to_matrix().to_4x4()
P = arm.pose.bones
def ang(a, b, c):  # interior angle at b
    return math.degrees((P[a].head - P[b].head).angle(P[c].head - P[b].head))
def tree(obj):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    pts = [ev.matrix_world @ v.co for v in m.vertices]; tris = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
    return pts, tris, BVHTree.FromPolygons(pts, tris)
rows = []
for t in (10, 13, 16, 20, 25, 30, 34, 40, 45, 48, 50, 53, 56, 59, 63):
    f = math.floor(t); bpy.context.scene.frame_set(f, subframe=t - f)
    if interaction.socket_at(config, t) == "bed":
        P["sword"].matrix = arm.matrix_world.inverted() @ SOCKET
    bpy.context.view_layer.update()
    row = {"t": t, "knee_flex": {s: round(180 - math.degrees((P[f"upper_leg.{s}"].head - P[f"lower_leg.{s}"].head).angle(P[f"foot.{s}"].head - P[f"lower_leg.{s}"].head)), 1) for s in "LR"},
           "hip_flex_vs_pelvis": {s: round(math.degrees((P["pelvis"].matrix.to_3x3() @ (arm.data.bones["pelvis"].matrix_local.to_3x3().inverted() @ Vector((0, 0, -1)))).angle(P[f"lower_leg.{s}"].head - P[f"upper_leg.{s}"].head)), 1) for s in "LR"},
           "elbow_R_flex": round(180 - math.degrees((P["upper_arm.R"].head - P["lower_arm.R"].head).angle(P["hand.R"].head - P["lower_arm.R"].head)), 1)}
    if t >= 44:
        sp, st, stree = tree(bpy.data.objects["SM_RO_sword"])
        hits = {}
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.name != "SM_RO_sword" and any(m.type == "ARMATURE" for m in obj.modifiers):
                bp, bt, btree = tree(obj); pairs = stree.overlap(btree)
                if pairs:
                    names = [g.name for g in obj.vertex_groups]
                    dom = collections.Counter(max(((names[g.group], g.weight) for g in obj.data.vertices[bt[j][0]].groups), key=lambda x: x[1], default=("?", 0))[0] for _, j in pairs)
                    hits[obj.name] = {"pairs": len(pairs), "bones": dict(dom.most_common(3))}
        row["sword_hits"] = hits
    rows.append(row); print("ROW " + json.dumps(row))
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(rows, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
