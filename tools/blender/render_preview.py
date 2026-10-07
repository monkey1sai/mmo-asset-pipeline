"""Render fixed preview views of GLB files (Blender 4.x, headless, EEVEE): a three-quarter view, a front view and a top
view per file, framed on the model's bounds, under one key light and a neutral grey floor. For art-match evidence;
not a game render. Usage:
  blender -b --python tools/blender/render_preview.py -- --out <dir> <a.glb> [<b.glb> ...]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bounds(objects):
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo = Vector(min(lo[i], world[i]) for i in range(3))
            hi = Vector(max(hi[i], world[i]) for i in range(3))
    return lo, hi


def setup_world(center, radius):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'SceneEEVEE') and 'BLENDER_EEVEE_NEXT' in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('preview')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.12, 0.14, 0.18, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=radius * 12, location=(center.x, center.y, 0))
    floor = bpy.context.active_object
    floor.name = 'preview-floor'
    mat = bpy.data.materials.new('preview-floor')
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.30, 0.31, 0.28, 1)
    floor.data.materials.append(mat)
    bpy.ops.object.light_add(type='SUN', location=(center.x + radius, center.y - radius, center.z + radius * 2))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    bpy.ops.object.light_add(type='SUN', location=(center.x - radius, center.y + radius, center.z + radius))
    fill = bpy.context.active_object
    fill.data.energy = 0.8
    fill.rotation_euler = (math.radians(60), 0, math.radians(-140))


def render(center, radius, azimuth_deg, elevation_deg, path):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new('preview-camera')
    cam_data.lens = 35
    cam = bpy.data.objects.new('preview-camera', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    distance = radius * 2.6
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    position = center + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * distance
    cam.location = position
    direction = (center - position).normalized()
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cam_data)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    for path in args.files:
        clear_scene()
        bpy.ops.import_scene.gltf(filepath=path)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        lo, hi = bounds(meshes)
        center = (lo + hi) / 2
        radius = max((hi - lo).length / 2, 0.5)
        setup_world(center, radius)
        name = os.path.splitext(os.path.basename(path))[0]
        for view, (az, el) in {'three-quarter': (-125, 25), 'front': (-90, 8), 'top': (-90, 80)}.items():
            render(center, radius, az, el, os.path.join(args.out, f'{name}-{view}.png'))
        print('PREVIEW_OK', name, [round(v, 3) for v in lo], [round(v, 3) for v in hi])


if __name__ == '__main__':
    main()
