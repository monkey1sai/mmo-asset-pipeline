"""Clip frame probe (diagnostic): for given frames of a clip action, the lowest triangles with and without the corrective
rules, and the same frames with the sword sockets as the clip check sets them (hand rest attachment)."""
import json, sys
from pathlib import Path
import bpy
from mathutils import Quaternion
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_soup import Soup, tri_area
import cv1_pose_rules as rules_math
import cv1_interaction as interaction
clip_blend, interaction_path, contract_path, rules_path, frames_arg = sys.argv[sys.argv.index("--") + 1:][:5]
config = interaction.load(interaction_path)
contract = json.loads(Path(contract_path).read_text(encoding="utf-8")); rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
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
with bpy.data.libraries.load(str(ROOT / clip_blend), link=False) as (src, dst):
    dst.actions = [config["clip"]]
arm.animation_data_create(); arm.animation_data.action = dst.actions[0]
def pose_rel():
    out = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        out[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return out
out = {}
for f in [float(x) for x in frames_arg.split(",")]:
    bpy.context.scene.frame_set(int(f), subframe=f - int(f))
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []): key.value = 0.0
    bpy.context.view_layer.update()
    res = {}
    m = soup.measure(soup.evaluated_points())
    res["no_rules"] = {"min": round(m["min_triangle_area_ratio"], 4), "collapsed": [(e["triangle"], sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in m["collapsed_examples"]], "hand_self": m["hand_self_pairs"], "hand_other_new": m["hand_other_new_pairs"]}
    rel = pose_rel()
    for name, q in rules_math.helper_rotations(rules, rel, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(q); rel[name] = q
    bpy.context.view_layer.update()
    states = interaction.states_at(config, f)
    keys = sorted({d["key"] for d in rules["drivers"].values() if d["type"] == "state"})
    state = {k: float(states.get(k, 0.0)) for k in keys}
    weights = rules_math.evaluate(rules, rel, state)
    for (mesh, key), value in weights.items(): bpy.data.objects[mesh].data.shape_keys.key_blocks[key].value = value
    bpy.context.view_layer.update()
    m = soup.measure(soup.evaluated_points())
    res["rules"] = {"min": round(m["min_triangle_area_ratio"], 4), "collapsed": [(e["triangle"], sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in m["collapsed_examples"]], "hand_self": m["hand_self_pairs"], "hand_other_new": m["hand_other_new_pairs"], "hand_examples": m["hand_examples"][:6],
                    "state": state, "top_morphs": sorted(((round(v, 3), f"{mk[0]}/{mk[1]}") for mk, v in weights.items() if v > 0.05), reverse=True)[:8]}
    out[str(f)] = res
print("CV1_CLIP_FRAME_PROBE " + json.dumps(out))
