"""Does the frozen two_hand_chop pose alone (pelvis at rest, b20) collapse triangles? Diagnostic using the clip check's soup."""
import json, sys
from pathlib import Path
import bpy
from mathutils import Quaternion
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_soup import Soup
poses = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
contract = json.loads(Path(sys.argv[sys.argv.index("--") + 2]).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks[1:]: key.value = 0.0
bpy.context.view_layer.update()
limits = contract["limits"]
meshes = sorted((o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers) and o.name not in set(limits["excluded_meshes"])), key=lambda o: o.name)
soup = Soup(meshes, limits); soup.set_rest()
out = {}
for name in ("grasp.R", "two_hand_chop"):
    for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0)
    for bone, q in poses[name].items(): arm.pose.bones[bone].rotation_quaternion = Quaternion(q)
    bpy.context.view_layer.update()
    m = soup.measure(soup.evaluated_points())
    out[name] = {"collapsed": m["collapsed_triangles"], "min_ratio": round(m["min_triangle_area_ratio"], 4), "examples": [(e["triangle"], e["mesh"], sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in m["collapsed_examples"]], "hand_self": m["hand_self_pairs"], "hand_other_new": m["hand_other_new_pairs"]}
print("CV1_GUARD_PROBE " + json.dumps(out))
