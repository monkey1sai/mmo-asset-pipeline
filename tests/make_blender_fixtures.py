"""Synthetic technical fixtures only; not production character assets."""
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
if not output.is_relative_to(ROOT / "artifacts"):
    raise ValueError("Fixtures must stay in repository artifacts")
output.mkdir(parents=True, exist_ok=True)
profile = json.loads((ROOT / "configs/rig_profiles.json").read_text())["humanoid-v1"]


def cube():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add()
    return bpy.context.object


def save(name):
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (name + ".blend")))


obj = cube()
save("static")
bpy.ops.export_scene.fbx(filepath=str(output / "static.fbx"), use_selection=True, object_types={"MESH"}, bake_anim=False)
for layer in list(obj.data.uv_layers):
    obj.data.uv_layers.remove(layer)
save("no_uv")
obj = cube()
data = bpy.data.armatures.new("FixtureRig")
rig = bpy.data.objects.new("ARM_Fixture", data)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
obj.select_set(False)
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for index, (name, parent) in enumerate(profile["bones"].items()):
    bone = data.edit_bones.new(name)
    bone.head = (0, 0, index * 0.1)
    bone.tail = (0, 0, index * 0.1 + 0.08)
    if parent:
        bone.parent = data.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")
modifier = obj.modifiers.new("FixtureArmature", "ARMATURE")
modifier.object = rig
group = obj.vertex_groups.new(name="pelvis")
group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
save("skin_valid")
bpy.ops.mesh.primitive_cube_add()
helmet = bpy.context.object
helmet.parent = rig
helmet.parent_type = "BONE"
helmet.parent_bone = "head"
save("rigid_valid")
bpy.data.objects.remove(helmet, do_unlink=True)
group.add(list(range(len(obj.data.vertices))), 0.5, "REPLACE")
save("bad_sum")
obj.vertex_groups.clear()
for name in list(profile["bones"])[1:6]:
    group = obj.vertex_groups.new(name=name)
    group.add(list(range(len(obj.data.vertices))), 0.2, "REPLACE")
save("too_many")
obj.vertex_groups.clear()
group = obj.vertex_groups.new(name="artist_selection_not_a_bone")
group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
save("non_deform_groups")
obj.vertex_groups.clear()
group = obj.vertex_groups.new(name="pelvis")
group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
data.edit_bones["hand_r"].parent = data.edit_bones["root"]
bpy.ops.object.mode_set(mode="OBJECT")
save("bad_parent")
