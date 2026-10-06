"""Self-test of scripts/cv1_foundation_signature.py on throwaway copies of the current candidate.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python <this file> -- <scratch dir>
Saves three copies into the scratch directory (outside the repository): one with an extra action keyed on
the armature, one with one weight changed by 0.01, one with one shape-key vertex moved by 0.1 mm. The
signature tool is then run on each by the caller; only the first must keep every category unchanged.
"""
from pathlib import Path
import sys

import bpy

scratch = Path(sys.argv[sys.argv.index("--") + 1])
scratch.mkdir(parents=True, exist_ok=False)
source = bpy.data.filepath
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))

# 1. a new clip only
action = bpy.data.actions.new("AN_SelfTest_NewClip")
arm.animation_data_create()
arm.animation_data.action = action
for frame, angle in ((0, 0.0), (30, 0.6)):
    arm.pose.bones["upper_arm.R"].rotation_quaternion = (1, 0, 0, 0) if angle == 0 else (0.955, 0.296, 0, 0)
    arm.pose.bones["upper_arm.R"].keyframe_insert("rotation_quaternion", frame=frame)
bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "added-clip.blend"), copy=True)

# 2. one weight changed
bpy.ops.wm.open_mainfile(filepath=source, load_ui=False)
core = bpy.data.objects["SM_RO_core"]
vertex = next(v for v in core.data.vertices if len(v.groups) >= 2)
group = vertex.groups[0]
core.vertex_groups[group.group].add([vertex.index], max(0.0, group.weight - 0.01), "REPLACE")
bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "changed-weight.blend"), copy=True)

# 3. one corrective vertex moved
bpy.ops.wm.open_mainfile(filepath=source, load_ui=False)
hand = bpy.data.objects["SM_RO_hand.R"]
key = hand.data.shape_keys.key_blocks["SKC_fist.R"]
key.data[0].co.x += 0.0001
bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "changed-morph.blend"), copy=True)
print("CV1_SIGNATURE_SELFTEST_FILES", sorted(p.name for p in scratch.iterdir()))
