"""Diagnostic (report only): bed-socket candidates beside the right hand of the Sleep posture (posture-01, head towards +X).
Supine pelvis: turns x -90 then z -90 at (0, 0.65, rest z + posture lift); posture-01 steps applied. For grip points near
the right hand and blade directions on the bed plane, the flat-lying rolls (least vertical extent of SM_RO_sword) are
tried with the grip lifted so the sword's lowest point is 1 mm above the bed top; the least wrist bend over elbow swivel
and the gap between the sword and the body (core, coat, bracer, hand meshes) are reported."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
from cv1_contract_pose import ContractPoser
posture = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1/v001/clips/AN_RO_Sleep_Loop/posture-01/posture.json").read_text(encoding="utf-8"))
base = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1/v001/clips/AN_RO_Sleep_Loop/posture-01/base.json").read_text(encoding="utf-8"))
contract = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {})
poser.reset()
bones = arm.data.bones
head, rest = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
turn = Quaternion(Vector((0, 0, 1)), math.radians(-90)) @ Quaternion(Vector((1, 0, 0)), math.radians(-90))
arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0.0, 0.65, head.z + posture["pelvis"]["lift_m"]))) @ (turn.to_matrix() @ rest).to_4x4()
bpy.context.view_layer.update()
for step in base["steps"] + posture["solved_steps"]:
    pb = arm.pose.bones[step["bone"]]
    pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(step, step.get("side"), 1.0)
bpy.context.view_layer.update()
ik = ArmIK(arm)
hand_now = arm.pose.bones["hand.R"].head.copy()
sword = bpy.data.objects["SM_RO_sword"]
local = [bones["sword"].matrix_local.inverted() @ (sword.matrix_world @ v.co) for v in sword.data.vertices]
dg = bpy.context.evaluated_depsgraph_get()
body_pts, body_tris = [], []
for name in ("SM_RO_core", "SM_RO_coat", "SM_RO_bracer.R", "SM_RO_hand.R", "SM_RO_cuirass"):
    ev = bpy.data.objects[name].evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles(); base_i = len(body_pts)
    body_pts += [ev.matrix_world @ v.co for v in m.vertices]; body_tris += [tuple(base_i + i for i in t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
body_tree = BVHTree.FromPolygons(body_pts, body_tris)
rows = []
blades = {"to_feet": (-1, 0, 0), "to_head": (1, 0, 0), "outward": (0, -1, 0), "feet_out": (-0.8, -0.6, 0), "head_out": (0.8, -0.6, 0)}
for dx in (-0.10, 0.0, 0.10):
    for dy in (-0.04, -0.10):
        g = hand_now + Vector((dx, dy, 0.0))
        for bname, b in blades.items():
            flat = sorted(((max(p.z for p in pts) - min(p.z for p in pts), roll) for roll in range(0, 360, 5)
                           for pts in [[sword_world(Vector((g.x, g.y, 0.0)), Vector(b), math.radians(roll)) @ q for q in local]]))[:2]
            for extent, roll in flat:
                m0 = sword_world(Vector((g.x, g.y, 0.0)), Vector(b), math.radians(roll))
                lift = 0.451 - min((m0 @ q).z for q in local)
                socket = sword_world(Vector((g.x, g.y, lift)), Vector(b), math.radians(roll))
                pts = [socket @ q for q in local]
                gap = min((body_tree.find_nearest(p)[3] or 9.0) for p in pts[::7])
                best = ik.best_swivel("R", ik.hand_for_sword(socket))
                rows.append({"grip": [round(g.x, 3), round(g.y, 3), round(lift, 4)], "blade": bname, "roll": roll, "body_gap_m": round(gap, 4),
                             **({"wrist_bend_deg": round(best[0], 1), "swivel": best[1]} if best else {"reachable": False})})
rows.sort(key=lambda r: r.get("wrist_bend_deg", 999))
out = {"hand_R_head_m": list(hand_now), "shoulder_R_m": list(ik.shoulder("R")), "rows": rows}
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("SUPINE hand %s shoulder %s" % ([round(c, 3) for c in hand_now], [round(c, 3) for c in ik.shoulder("R")]))
for r in rows[:10]:
    print("SCAN", json.dumps(r))
print("SCAN reachable %d of %d" % (sum(1 for r in rows if "wrist_bend_deg" in r), len(rows)))
