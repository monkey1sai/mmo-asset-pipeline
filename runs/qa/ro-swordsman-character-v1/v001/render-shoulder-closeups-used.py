"""Render gray close-ups of both shoulders at rest and with the pauldron hidden (read-only).
Run: blender -b --factory-startup --disable-autoexec <blend> --python <this> -- <out dir>"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=False)
s = bpy.context.scene
s.render.engine = "BLENDER_WORKBENCH"; s.display.shading.light = "STUDIO"; s.display.shading.color_type = "SINGLE"
s.display.shading.single_color = (0.62, 0.62, 0.62); s.display.shading.show_cavity = True
s.render.resolution_x = s.render.resolution_y = 640
cam = bpy.data.objects.new("CloseCam", bpy.data.cameras.new("CloseCam")); s.collection.objects.link(cam); s.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.45
for o in bpy.data.objects:
    if o.type == "MESH" and o.name == "Plane": o.hide_render = True
for side, sign in (("L", 1), ("R", -1)):
    target = Vector((0.2 * sign, 0.04, 1.28))
    for view, offset in (("front", Vector((0.35 * sign, -1.6, 0.25))), ("side", Vector((1.6 * sign, 0.1, 0.2))), ("back", Vector((0.35 * sign, 1.6, 0.25)))):
        cam.location = target + offset
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        for hidden in (False, True):
            bpy.data.objects[f"SM_RO_pauldron.{side}"].hide_render = hidden
            s.render.filepath = str(out / f"{side}-{view}-{'no-pauldron' if hidden else 'rest'}.png")
            bpy.ops.render.render(write_still=True)
        bpy.data.objects[f"SM_RO_pauldron.{side}"].hide_render = False
print("done")
