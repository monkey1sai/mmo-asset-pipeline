"""LieDown preparation (report only): seated pelvis height, rest ankles, seated leg IK angles and the put-down arm solve.
Seated: pelvis head (0, 0.32, z) leaned back 10 deg (world x turn -10), z so the lowest pelvis-weighted core vertex is 5 mm
above the bed top; ankles moved forward to y -0.30 (feet flat at rest orientation); put-down: spine_02 15 deg right,
clavicle.R 10 deg down, right hand on the bed socket (bed-interaction-design.json)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, LegIK
from cv1_contract_pose import ContractPoser
contract = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
design = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1/v001/clips/bed-interaction-design.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {}); poser.reset(); bpy.context.view_layer.update()
bones = arm.data.bones
legik, armik = LegIK(arm), ArmIK(arm)
rest_ankles = {s: list(legik.foot_rest[s].translation) for s in "LR"}
head, rest = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
lean = Quaternion(Vector((1, 0, 0)), math.radians(-10.0))
core = bpy.data.objects["SM_RO_core"]; pg = core.vertex_groups["pelvis"].index
ids = [v.index for v in core.data.vertices if any(g.group == pg and g.weight >= 0.5 for g in v.groups)]
def lowest():
    dg = bpy.context.evaluated_depsgraph_get(); ev = core.evaluated_get(dg); m = ev.to_mesh()
    z = min((ev.matrix_world @ m.vertices[i].co).z for i in ids); ev.to_mesh_clear(); return z
z = head.z - 0.30
for _ in range(6):
    arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0, 0.32, z))) @ (lean.to_matrix() @ rest).to_4x4(); bpy.context.view_layer.update()
    z += 0.455 - lowest()
arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0, 0.32, z))) @ (lean.to_matrix() @ rest).to_4x4(); bpy.context.view_layer.update()
legs = {}
for s in "LR":
    a = Vector(rest_ankles[s]); a.y = -0.30
    sol = legik.solve(s, Matrix.Translation(a) @ legik.foot_rest[s].to_3x3().to_4x4())
    up, lo = arm.pose.bones[f"upper_leg.{s}"], arm.pose.bones[f"lower_leg.{s}"]
    pelvis_down = (arm.pose.bones["pelvis"].matrix.to_3x3() @ (rest.inverted() @ Vector((0, 0, -1)))).normalized()
    thigh = (up.tail - up.head).normalized()
    legs[s] = {"ankle_m": list(a), **sol, "knee_flexion_deg": 180 - sol["knee_angle_deg"], "hip_flexion_deg_vs_pelvis_down": math.degrees(pelvis_down.angle(thigh)),
               "upper_leg_local_wxyz": list(up.rotation_quaternion), "lower_leg_local_wxyz": list(lo.rotation_quaternion)}
for step in ({"bone": "spine_02", "kind": "swing", "toward": "right", "degrees": 15}, {"bone": "clavicle.R", "kind": "swing", "toward": "down", "degrees": 10, "side": "R"}):
    pb = arm.pose.bones[step["bone"]]; pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(step, step.get("side"), 1.0)
bpy.context.view_layer.update()
sock = design["sword_bed_socket"]
target = armik.hand_for_sword(Matrix.Translation(Vector(sock["head_m"])) @ Quaternion(sock["quaternion_wxyz"]).to_matrix().to_4x4())
best = armik.best_swivel("R", target)
put = armik.solve("R", target, best[1]) if best else None
out = {"seat_pelvis_head_m": [0.0, 0.32, z], "lean_back_deg": 10, "pelvis_rest_head_m": list(head), "rest_ankles_m": rest_ankles, "seated_legs": legs,
       "put_down": {"best_swivel": best, "solve": put}}
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("PREP " + json.dumps({"seat_z": round(z, 4), "rest_ankles": {s: [round(c, 4) for c in v] for s, v in rest_ankles.items()},
                            "legs": {s: {k: round(v[k], 2) for k in ("knee_flexion_deg", "hip_flexion_deg_vs_pelvis_down", "ankle_error_mm")} for s, v in legs.items()},
                            "put_down": {"swivel": best[1] if best else None, "wrist_bend": round(best[0], 1) if best else None, "solve": put}}))
