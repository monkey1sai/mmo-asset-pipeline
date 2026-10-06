"""Diagnostic (report only): sword planted point-down in the floor in front of the bed's near face, reached while seated.
Seated pelvis as seated-prep (head (0, 0.32, 0.5545)), lean back 0/5/10 deg; grip right of the knees in front of the near face;
blade straight down or tilted back/out a few degrees, tip 2 cm into the floor (grip-to-tip 0.935 m); roll searched.
Reports least wrist bend, reach and the gap to the seated body (core, coat, bracer, cuirass, pauldron)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
from cv1_contract_pose import ContractPoser
contract = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {})
bones = arm.data.bones
head, rest = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
sword = bpy.data.objects["SM_RO_sword"]
local = [bones["sword"].matrix_local.inverted() @ (sword.matrix_world @ v.co) for v in sword.data.vertices]
tip_local = max(local, key=lambda q: q.y)  # blade runs along the bone's +Y: the tip has the largest local y
ik = ArmIK(arm)
rows = []
for lean in (0, 5, 10):
    poser.reset()
    arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0, 0.32, 0.5545))) @ (Quaternion(Vector((1, 0, 0)), math.radians(-lean)).to_matrix() @ rest).to_4x4()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); pts, tris = [], []
    for name in ("SM_RO_core", "SM_RO_coat", "SM_RO_bracer.R", "SM_RO_cuirass", "SM_RO_pauldron.R"):
        ev = bpy.data.objects[name].evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles(); b = len(pts)
        pts += [ev.matrix_world @ v.co for v in m.vertices]; tris += [tuple(b + i for i in t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
    tree = BVHTree.FromPolygons(pts, tris)
    for gx in (-0.40, -0.45, -0.50):
        for gy in (-0.05, 0.05, 0.12):
            for bname, b in {"down": (0, 0, -1), "down_back5": (0, math.sin(math.radians(5)), -math.cos(math.radians(5))), "down_out5": (-math.sin(math.radians(5)), 0, -math.cos(math.radians(5)))}.items():
                best = None
                for roll in range(0, 360, 10):
                    m0 = sword_world(Vector((gx, gy, 0.0)), Vector(b), math.radians(roll))
                    gz = -0.02 - (m0 @ tip_local).z
                    socket = sword_world(Vector((gx, gy, gz)), Vector(b), math.radians(roll))
                    option = ik.best_swivel("R", ik.hand_for_sword(socket))
                    if option and (best is None or option[0] < best[0]):
                        best = (option[0], roll, option[1], gz, socket)
                if best:
                    gap = min((tree.find_nearest(best[4] @ q)[3] or 9.0) for q in local[::5])
                    rows.append({"lean_back": lean, "grip": [gx, gy, round(best[3], 3)], "blade": bname, "roll": best[1], "swivel": best[2], "wrist_bend_deg": round(best[0], 1), "body_gap_m": round(gap, 3)})
rows.sort(key=lambda r: r["wrist_bend_deg"])
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(rows, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
for r in rows[:10]:
    print("SCAN", json.dumps(r))
print("SCAN reachable rows %d of %d" % (len(rows), 3 * 3 * 3 * 3))
