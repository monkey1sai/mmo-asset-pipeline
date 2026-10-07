"""Guard pose with the corrective rules on (grasp.R 1, grasp.L 1) and the pelvis at the endure height: which triangles collapse? Diagnostic."""
import json, sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Matrix, Vector
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_soup import Soup
import cv1_pose_rules as rules_math
poses = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
contract = json.loads(Path(sys.argv[sys.argv.index("--") + 2]).read_text(encoding="utf-8"))
rules = json.loads(Path(sys.argv[sys.argv.index("--") + 3]).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
for pb in arm.pose.bones: pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
for obj in skinned:
    for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []): key.value = 0.0
bpy.context.view_layer.update()
limits = contract["limits"]
meshes = sorted((o for o in skinned if o.name not in set(limits["excluded_meshes"])), key=lambda o: o.name)
soup = Soup(meshes, limits); soup.set_rest()
def pose_rel():
    out = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        out[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return out
out = {}
for label, correctives, pelvis_z in (("guard_rest_norules", False, 0.89), ("guard_rest_rules", True, 0.89), ("guard_low_rules", True, 0.78), ("guard_low_norules", False, 0.78)):
    for pb in arm.pose.bones: pb.location, pb.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []): key.value = 0.0
    for bone, q in poses["two_hand_chop"].items(): arm.pose.bones[bone].rotation_quaternion = Quaternion(q)
    pb = arm.pose.bones["pelvis"]; pb.matrix = Matrix.Translation(Vector((0, 0.04, pelvis_z))) @ bones["pelvis"].matrix_local.to_3x3().to_4x4()
    bpy.context.view_layer.update()
    if correctives:
        rel = pose_rel()
        for name, q in rules_math.helper_rotations(rules, rel, REST_LOCAL, PARENTS).items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(q); rel[name] = q
        bpy.context.view_layer.update()
        state = {"grasp.R": 1.0, "grasp.L": 1.0, "lying": 0.0}
        for (mesh, key), value in rules_math.evaluate(rules, rel, state).items():
            bpy.data.objects[mesh].data.shape_keys.key_blocks[key].value = value
        bpy.context.view_layer.update()
    m = soup.measure(soup.evaluated_points())
    out[label] = {"collapsed": m["collapsed_triangles"], "min_ratio": round(m["min_triangle_area_ratio"], 4), "examples": [(e["triangle"], sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in m["collapsed_examples"]], "hand_self": m["hand_self_pairs"], "hand_other_new": m["hand_other_new_pairs"]}
print("CV1_GUARD_PROBE2 " + json.dumps(out))
