"""Diagnostic (report only): which meshes the socketed sword crosses in Sleep a01 at frame 0 (clip-check evaluation order)."""
import json, math, sys, collections
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction, cv1_pose_rules as rules_math
config = interaction.load(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_Sleep_Loop/interaction.json")
rules = json.loads((ROOT / "assets/processed/ro-swordsman-character-v1/v001/b18-clipfolds/corrective-rules.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(str(ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_Sleep_Loop/a01/AN_RO_Sleep_Loop.blend"), link=False) as (s, d):
    d.actions = ["AN_RO_Sleep_Loop"]
arm.animation_data_create(); arm.animation_data.action = bpy.data.actions["AN_RO_Sleep_Loop"]
bpy.context.scene.frame_set(0)
sock = config["sword_socket"]["bed_socket"]
arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ (Matrix.Translation(Vector(sock["head_m"])) @ Quaternion(sock["quaternion_wxyz"]).to_matrix().to_4x4())
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
def tree(obj):
    ev = obj.evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles()
    pts = [ev.matrix_world @ v.co for v in m.vertices]; tris = [tuple(t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
    return pts, tris, BVHTree.FromPolygons(pts, tris)
sp, st, stree = tree(bpy.data.objects["SM_RO_sword"])
out = {}
for obj in bpy.data.objects:
    if obj.type != "MESH" or obj.name == "SM_RO_sword" or not any(m.type == "ARMATURE" for m in obj.modifiers):
        continue
    bp, bt, btree = tree(obj)
    pairs = stree.overlap(btree)
    if pairs:
        cent = [sum((bp[i] for i in bt[j]), Vector()) / 3 for _, j in pairs]
        groups = obj.vertex_groups
        dom = collections.Counter(max(((groups[g.group].name, g.weight) for g in obj.data.vertices[bt[j][0]].groups), key=lambda x: x[1], default=("?", 0))[0] for _, j in pairs)
        out[obj.name] = {"pairs": len(pairs), "x": [round(min(c.x for c in cent), 3), round(max(c.x for c in cent), 3)], "y": [round(min(c.y for c in cent), 3), round(max(c.y for c in cent), 3)],
                         "z": [round(min(c.z for c in cent), 3), round(max(c.z for c in cent), 3)], "dominant_bones": dict(dom.most_common(4))}
print("DIAG_SWORD " + json.dumps(out))
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
