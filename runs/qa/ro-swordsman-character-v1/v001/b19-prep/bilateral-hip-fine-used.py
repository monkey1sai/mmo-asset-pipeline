"""Diagnostic (report only, fine variant): b18 under bilateral hip flexion (both upper_leg twist about right, contract hip-flexion
vocabulary) from 50 to 90 deg, knees straight or flexed 40 deg; helpers and correctives evaluated as in the clip check
(interaction states 0). Lists collapsed triangles (< 5% rest area) and the minimum ratio per pose."""
import json, sys
from pathlib import Path
import bpy
from mathutils import Quaternion
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser
from cv1_soup import Soup
contract = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
rules = json.loads((ROOT / sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
out_path = ROOT / sys.argv[sys.argv.index("--") + 2]
limits = contract["limits"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {})
B = arm.data.bones
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in B}
PARENTS = {b.name: b.parent.name if b.parent else None for b in B}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
def zero():
    for o in skinned:
        for k in (o.data.shape_keys.key_blocks[1:] if o.data.shape_keys else []):
            k.value = 0.0
def pose_rel():
    out = {}
    for pb in arm.pose.bones:
        rl = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        lo = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        out[pb.name] = tuple((rl.inverted() @ lo).to_quaternion())
    return out
poser.reset(); zero(); bpy.context.view_layer.update()
soup = Soup(meshes, limits); soup.set_rest()
rows = []
for knee in (0,):
    for hip in [x / 2 for x in range(110, 181, 5)]:
        poser.reset(); zero()
        for side in "LR":
            for step in ({"bone": f"upper_leg.{side}", "kind": "twist", "about": "right", "degrees": hip}, {"bone": f"lower_leg.{side}", "kind": "twist", "about": "left", "degrees": knee}):
                pb = arm.pose.bones[step["bone"]]
                pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(step, side, 1.0)
        bpy.context.view_layer.update()
        pose = pose_rel()
        for name, q in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(q); pose[name] = q
        bpy.context.view_layer.update()
        state = {d["key"]: 0.0 for d in rules["drivers"].values() if d["type"] == "state"}
        for (m, k), v in rules_math.evaluate(rules, pose, state).items():
            bpy.data.objects[m].data.shape_keys.key_blocks[k].value = v
        bpy.context.view_layer.update()
        res = soup.measure(soup.evaluated_points())
        pts = soup.evaluated_points()
        from cv1_soup import tri_area
        low = sorted((tri_area(pts, t) / a, i) for i, (t, a) in enumerate(zip(soup.tris, soup.rest_area)) if a > limits["min_rest_triangle_area_m2"])
        row = {"hip": hip, "knee": knee, "collapsed": res["collapsed_triangles"], "min_ratio": round(res["min_triangle_area_ratio"], 4),
               "below_7pct": [(i, round(r, 4), soup.centre(soup.rest, i)) for r, i in low if r < 0.07][:6]}
        rows.append(row); print("SWEEP " + json.dumps(row))
out_path.write_text(json.dumps(rows, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
