"""Evidence render (report only), close-up variant: a clip frame with the bed proxy drawn as a wireframe, so body parts inside the bed show.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-bed-render-used.py -- \
       <action .blend> <action name> <frame> <interaction.json> <view axis x|y|y-back|below> <out.png> [MESH:KEY=value ...]
Workbench render, one orthographic side view looking along +X or +Y. The sword sits on the interaction config's bed
socket when the frame is at or after its switch event. Skinning only (helpers and correctives off); nothing is saved.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
action_blend, action_name, frame, interaction_path, axis, out = argv[:6]
key_values = dict(item.split("=") for item in argv[6:] if not item.startswith("step:"))  # optional MESH:KEY=value pairs
extra_steps = [item.split(":")[1:] for item in argv[6:] if item.startswith("step:")]  # step:bone:toward:degrees:side (contract swings)
frame = int(frame)
config = json.loads(Path(interaction_path).read_text(encoding="utf-8"))
cx, cy = config["bed"]["centre_m"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [action_name]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
scene = bpy.context.scene
scene.frame_set(frame)
socket = config.get("sword_socket")
if socket:
    events = {e["name"]: e["frame"] for e in config["events"]}
    at = socket["initial"]
    for switch in socket["switches"]:
        if frame >= events[switch["event"]]:
            at = switch["to"]
    if at == "bed":
        head, quat = socket["bed_socket"]["head_m"], socket["bed_socket"]["quaternion_wxyz"]
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ (Matrix.Translation(Vector(head)) @ Quaternion(quat).to_matrix().to_4x4())
        bpy.context.view_layer.update()
if extra_steps:
    sys.path.insert(0, "C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/scripts")
    from cv1_contract_pose import ContractPoser
    contract = json.loads(Path("C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
    poser = ContractPoser(arm, contract, {})
    arm.animation_data.action = None  # keep the evaluated frame and add the extra steps on top
    for bone, toward, degrees, side in extra_steps:
        pb = arm.pose.bones[bone]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation({"bone": bone, "kind": "swing", "toward": toward, "degrees": float(degrees)}, side, 1.0)
    bpy.context.view_layer.update()
for name, value in key_values.items():
    mesh_name, key_name = name.split(":")
    bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = float(value)
for other in bpy.data.objects:
    if other.type == "MESH" and other.name == "Plane":
        other.hide_render = True  # the foundation's ground plane would hide a view from below
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, 0.45 / 2))
bed = bpy.context.active_object
bed.scale = (2.0, 0.9, 0.45)
bed.display_type = "WIRE"
bed.show_in_front = True
mod = bed.modifiers.new("wire", "WIREFRAME")
mod.thickness = 0.006
mat = bpy.data.materials.new("bed_wire")
mat.diffuse_color = (0.9, 0.1, 0.1, 1.0)
bed.data.materials.append(mat)
# Bed top plane as a thin translucent sheet for the line where things enter the bed.
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(cx, cy, 0.45))
top = bpy.context.active_object
top.scale = (2.0, 0.9, 1.0)
top_mat = bpy.data.materials.new("bed_top")
top_mat.diffuse_color = (0.2, 0.4, 0.9, 0.25)
top.data.materials.append(top_mat)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 2.4
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
if axis == "y":
    cam.location = (cx, cy - 4.0, 0.55)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
elif axis == "y-back":
    cam.location = (cx, cy + 4.0, 0.55)
    cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))
elif axis == "below":
    cam.location = (cx - 0.3, cy, -3.0)
    cam.rotation_euler = (math.radians(180.0), 0.0, 0.0)
    bed.hide_render = True
    top.hide_render = True
elif axis.startswith("top"):
    # top:x,y,scale  orthographic view straight down onto the given point
    tx, ty, scale = (float(v) for v in axis.split(":")[1].split(","))
    cam_data.ortho_scale = scale
    cam.location = (tx, ty, 3.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    bed.hide_render = True
    top.hide_render = True
elif axis.startswith("close"):
    # close:x,y,z,scale  orthographic close-up looking along +Y (from the front of the bed) at the given point
    cx2, cy2, cz2, scale = (float(v) for v in axis.split(":")[1].split(","))
    cam_data.ortho_scale = scale
    cam.location = (cx2, cy2 - 2.0, cz2)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
elif axis == "low-back":
    # From the feet end, low over the bed top, looking back along +X at the coat under the thighs.
    cam_data.type = "PERSP"
    cam.location = (cx - 1.6, cy - 0.35, 0.53)
    cam.rotation_euler = (math.radians(88.0), 0.0, math.radians(-75.0))
else:
    cam.location = (cx - 4.0, cy, 0.55)
    cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(-90.0))
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_xray = False
scene.render.resolution_x, scene.render.resolution_y = 1600, 700
scene.render.film_transparent = False
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("CV1_RENDER", out)
