"""Render the five fixed quality-protocol views of a character V1 candidate (rest pose, all shape keys at 0).

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_protocol_views.py -- --out <new dir>
Uses the review stage, lights and camera rule stored with the baseline (runs/qa/ro-swordsman-combo-r007/baseline/ro_review_common.py),
so candidates are rendered under the same conditions as the baseline views. The BLEND is not saved.
"""
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runs/qa/ro-swordsman-combo-r007/baseline"))
import ro_review_common as common

out = (ROOT / sys.argv[sys.argv.index("--out") + 1]).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
scene = bpy.context.scene
scene.camera = bpy.data.objects["ReviewCamera"]
for obj in bpy.data.objects:
    if obj.type == "ARMATURE":
        for pb in obj.pose.bones:
            pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    if obj.type == "MESH" and obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0
common.render_views(out, 1)
print("CV1_PROTOCOL_VIEWS", sorted(p.name for p in out.glob("*.png")))
