"""Diagnostic (report only): bed-socket candidates for laying the sword down while seated on the bed edge.
Seated torso: pelvis leaned back 15 deg, moved back onto the bed (head y 0.30) and lowered until the lowest pelvis-weighted
point rests 5 mm above the bed top (0.45 m). For each grip point on the bed top beside the right hip and each horizontal
blade direction, the roll that lays the sword flat (least vertical extent of SM_RO_sword) is kept (both flat rolls are
tried), the grip is lifted so the sword's lowest point is 1 mm above the bed top, and the least wrist bend over elbow
swivel is reported. Bend is the hand's rotation away from the forearm-carried rest relation (twist included)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
bpy.context.view_layer.update()
bones = arm.data.bones
head, rest = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
lean = Quaternion(Vector((1, 0, 0)), math.radians(-15.0))
core = bpy.data.objects["SM_RO_core"]
pelvis_group = core.vertex_groups["pelvis"].index
pelvis_ids = [v.index for v in core.data.vertices if any(g.group == pelvis_group and g.weight >= 0.5 for g in v.groups)]
def lowest_pelvis():
    dg = bpy.context.evaluated_depsgraph_get(); ev = core.evaluated_get(dg); m = ev.to_mesh()
    z = min((ev.matrix_world @ m.vertices[i].co).z for i in pelvis_ids); ev.to_mesh_clear(); return z
z = head.z - 0.30
for _ in range(6):
    arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0.0, 0.30, z))) @ (lean.to_matrix() @ rest).to_4x4()
    bpy.context.view_layer.update()
    z += 0.455 - lowest_pelvis()
arm.pose.bones["pelvis"].matrix = Matrix.Translation(Vector((0.0, 0.30, z))) @ (lean.to_matrix() @ rest).to_4x4()
bpy.context.view_layer.update()
ik = ArmIK(arm)
sword = bpy.data.objects["SM_RO_sword"]
local = [bones["sword"].matrix_local.inverted() @ (sword.matrix_world @ v.co) for v in sword.data.vertices]
rows = []
for gx in (-0.36, -0.42, -0.50):
    for gy in (0.26, 0.32, 0.38):
        for bname, b in {"outward": (-1, 0, 0), "outward_back": (-0.94, 0.34, 0), "outward_front": (-0.94, -0.34, 0)}.items():
            flat = sorted(((max(p.z for p in pts) - min(p.z for p in pts), roll) for roll in range(0, 360, 5)
                           for pts in [[sword_world(Vector((gx, gy, 0.0)), Vector(b), math.radians(roll)) @ q for q in local]]))[:2]
            for extent, roll in flat:
                m0 = sword_world(Vector((gx, gy, 0.0)), Vector(b), math.radians(roll))
                lift = 0.451 - min((m0 @ q).z for q in local)
                target = ik.hand_for_sword(sword_world(Vector((gx, gy, lift)), Vector(b), math.radians(roll)))
                best = ik.best_swivel("R", target)
                rows.append({"grip": [gx, gy, round(lift, 4)], "blade": bname, "roll": roll, "extent_m": round(extent, 4),
                             **({"wrist_bend_deg": round(best[0], 1), "swivel": best[1]} if best else {"reachable": False})})
rows.sort(key=lambda r: r.get("wrist_bend_deg", 999))
out = {"seated_pelvis_head_m": [0.0, 0.30, round(z, 4)], "lean_back_deg": 15.0, "shoulder_R_m": list(ik.shoulder("R")), "rows": rows}
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("SEAT pelvis head z %.4f shoulder %s" % (z, [round(c, 3) for c in ik.shoulder("R")]))
for r in rows[:8]:
    print("SCAN", json.dumps(r))
print("SCAN reachable %d of %d" % (sum(1 for r in rows if "wrist_bend_deg" in r), len(rows)))
