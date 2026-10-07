"""Diagnostic (report only): bed socket on the bed top beside the right hip, reached while seated with a right lean.
Seated torso as seated-scan (pelvis leaned back 10 deg, head y 0.32, lowest pelvis point 5 mm above the bed top), then
spine_02 swing toward right (lean) and clavicle.R swing toward down. Grip points on the bed top right of the hip, blade
outward (-X) or outward-back, flat rolls; reports least wrist bend, the arm's reach margin and the sword-body gap."""
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
lean_back = Quaternion(Vector((1, 0, 0)), math.radians(-10.0))
core = bpy.data.objects["SM_RO_core"]
pg = core.vertex_groups["pelvis"].index
pelvis_ids = [v.index for v in core.data.vertices if any(g.group == pg and g.weight >= 0.5 for g in v.groups)]
sword = bpy.data.objects["SM_RO_sword"]
local = [bones["sword"].matrix_local.inverted() @ (sword.matrix_world @ v.co) for v in sword.data.vertices]
ik = ArmIK(arm)
reach = ik.length["R"]
def lowest_pelvis():
    dg = bpy.context.evaluated_depsgraph_get(); ev = core.evaluated_get(dg); m = ev.to_mesh()
    z = min((ev.matrix_world @ m.vertices[i].co).z for i in pelvis_ids); ev.to_mesh_clear(); return z
def seat(lean, drop):
    poser.reset()
    z = head.z - 0.30
    for _ in range(5):
        arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0.0, 0.32, z))) @ (lean_back.to_matrix() @ rest).to_4x4()
        bpy.context.view_layer.update()
        z += 0.455 - lowest_pelvis()
    arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0.0, 0.32, z))) @ (lean_back.to_matrix() @ rest).to_4x4()
    bpy.context.view_layer.update()
    for step in ({"bone": "spine_02", "kind": "swing", "toward": "right", "degrees": lean}, {"bone": "clavicle.R", "kind": "swing", "toward": "down", "degrees": drop, "side": "R"}):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(step, step.get("side"), 1.0)
    bpy.context.view_layer.update()
def body_tree():
    dg = bpy.context.evaluated_depsgraph_get(); pts, tris = [], []
    for name in ("SM_RO_core", "SM_RO_coat", "SM_RO_bracer.R", "SM_RO_cuirass", "SM_RO_pauldron.R"):
        ev = bpy.data.objects[name].evaluated_get(dg); m = ev.to_mesh(); m.calc_loop_triangles(); b = len(pts)
        pts += [ev.matrix_world @ v.co for v in m.vertices]; tris += [tuple(b + i for i in t.vertices) for t in m.loop_triangles]; ev.to_mesh_clear()
    return BVHTree.FromPolygons(pts, tris)
rows = []
for lean in (0, 8, 15):
    for drop in (0, 10):
        seat(lean, drop)
        tree, shoulder = body_tree(), ik.shoulder("R")
        for gx in (-0.40, -0.45, -0.50):
            for gy in (0.26, 0.32):
                for bname, b in {"outward": (-1, 0, 0), "outward_back": (-0.94, 0.34, 0)}.items():
                    flat = sorted(((max(p.z for p in pts) - min(p.z for p in pts), roll) for roll in range(0, 360, 5)
                                   for pts in [[sword_world(Vector((gx, gy, 0.0)), Vector(b), math.radians(roll)) @ q for q in local]]))[:2]
                    for extent, roll in flat:
                        m0 = sword_world(Vector((gx, gy, 0.0)), Vector(b), math.radians(roll))
                        socket = sword_world(Vector((gx, gy, 0.451 - min((m0 @ q).z for q in local))), Vector(b), math.radians(roll))
                        target = ik.hand_for_sword(socket)
                        best = ik.best_swivel("R", target)
                        gap = min((tree.find_nearest(socket @ q)[3] or 9.0) for q in local[::5])
                        rows.append({"lean": lean, "clavicle_drop": drop, "grip": [gx, gy], "blade": bname, "roll": roll,
                                     "wrist_to_shoulder_m": round((target.translation - shoulder).length, 3), "arm_max_m": round(0.985 * sum(reach), 3),
                                     "body_gap_m": round(gap, 3), **({"wrist_bend_deg": round(best[0], 1), "swivel": best[1]} if best else {"reachable": False})})
ok = sorted((r for r in rows if "wrist_bend_deg" in r), key=lambda r: r["wrist_bend_deg"])
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps({"arm_lengths_m": list(reach), "rows": rows}, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("ARM upper %.3f lower %.3f max wrist distance %.3f" % (reach[0], reach[1], 0.985 * sum(reach)))
for r in ok[:8]:
    print("SCAN", json.dumps(r))
print("SCAN reachable %d of %d; nearest unreachable wrist distance %s" % (len(ok), len(rows), min((r["wrist_to_shoulder_m"] for r in rows if "wrist_bend_deg" not in r), default=None)))
