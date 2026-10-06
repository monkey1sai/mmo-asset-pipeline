"""Bed socket transform: sword flat on the bed top right of the seated hip (seated-lean-scan best row): grip (-0.40, 0.32),
blade along -X, roll 160 deg about the blade (least vertical extent), lowest sword point 1 mm above the bed top."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import sword_world
bones = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children)).data.bones
sword = bpy.data.objects["SM_RO_sword"]
local = [bones["sword"].matrix_local.inverted() @ (sword.matrix_world @ v.co) for v in sword.data.vertices]
grip, blade, roll = Vector((-0.40, 0.32, 0.0)), Vector((-1.0, 0.0, 0.0)), math.radians(160)
m0 = sword_world(grip, blade, roll)
grip.z = 0.451 - min((m0 @ q).z for q in local)
m = sword_world(grip, blade, roll)
pts = [m @ q for q in local]
q = m.to_quaternion()
out = {"head_m": [round(c, 6) for c in m.translation], "quaternion_wxyz": [q.w, q.x, q.y, q.z],
       "sword_extent_m": {"x": [min(p.x for p in pts), max(p.x for p in pts)], "y": [min(p.y for p in pts), max(p.y for p in pts)], "z": [min(p.z for p in pts), max(p.z for p in pts)]}}
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("SOCKET " + json.dumps(out))
