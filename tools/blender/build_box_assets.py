"""Build box-composed assets from a spec JSON and export each as a GLB (Blender 4.x, headless).

Usage:
  blender -b --python tools/blender/build_box_assets.py -- --spec <spec.json> --out <dir>

Spec (units metres, Y up, right-handed; glTF axes):
{
  "assets": [
    {"id": "cl-brazier", "parts": [
      {"name": "brazier-body", "boxes": [
        {"c": [x, y, z], "s": [sx, sy, sz], "color": "#rrggbb", "rot_y": 0.0},
        ...
      ]},
      {"name": "brazier-coals", "emissive": [4.5, 1.6, 0.35], "boxes": [...]}
    ]}
  ]
}

Each part becomes one mesh object (its boxes joined), named after the part, with one material per distinct colour
(Principled BSDF: base colour, roughness 0.85, metallic 0; parts with "emissive" get that emission colour and
strength 1). All parts of an asset share the origin at the asset's ground centre: the spec positions are already
relative to it. The tool knows nothing about any game: sizes, colours and names all come from the spec.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Vector


def srgb_hex_to_linear(value):
    value = value.lstrip('#')
    channels = [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material_for(cache, color_hex, emissive):
    key = (color_hex, tuple(emissive) if emissive else None)
    if key in cache:
        return cache[key]
    mat = bpy.data.materials.new(name=f"{color_hex.lstrip('#')}{'-emissive' if emissive else ''}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    linear = srgb_hex_to_linear(color_hex)
    bsdf.inputs['Base Color'].default_value = (*linear, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Metallic'].default_value = 0.0
    if emissive:
        bsdf.inputs['Emission Color'].default_value = (emissive[0], emissive[1], emissive[2], 1.0)
        bsdf.inputs['Emission Strength'].default_value = 1.0
    cache[key] = mat
    return mat


def add_box(collection, box, material):
    # Spec is glTF-like (x right, y up, z forward); Blender is z up: (x, y, z) -> (x, -z, y).
    cx, cy, cz = box['c']
    sx, sy, sz = box['s']
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, -cz, cy))
    obj = bpy.context.active_object
    obj.scale = (sx, sz, sy)
    rot_y = float(box.get('rot_y', 0.0))
    if rot_y:
        obj.rotation_euler = Euler((0.0, 0.0, -rot_y), 'XYZ')  # a yaw about glTF +Y is a yaw about Blender +Z, mirrored
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.material_index = 0
    return obj


def build_part(asset_id, part, material_cache):
    emissive = part.get('emissive')
    objects = []
    for box in part['boxes']:
        objects.append(add_box(None, box, material_for(material_cache, box['color'], emissive)))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objects) > 1:
        bpy.ops.object.join()
    merged = bpy.context.active_object
    merged.name = part['name']
    merged.data.name = part['name']
    # Origin at the asset's ground centre (world origin): the spec positions are relative to it already.
    bpy.context.scene.cursor.location = Vector((0.0, 0.0, 0.0))
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return merged


def export_asset(asset, out_dir):
    clear_scene()
    material_cache = {}
    parts = [build_part(asset['id'], part, material_cache) for part in asset['parts']]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    path = os.path.join(out_dir, f"{asset['id']}.glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_animations=False,
        export_skins=False,
        export_morph=False,
        export_lights=False,
        export_cameras=False,
        export_texcoords=False,
        export_normals=True,
        export_materials='EXPORT',
        export_image_format='NONE',
    )
    triangles = sum(len(obj.data.polygons) * 2 for obj in parts)  # every face is a quad
    return {
        'asset_id': asset['id'],
        'file': path,
        'parts': [obj.name for obj in parts],
        'quads': sum(len(obj.data.polygons) for obj in parts),
        'triangles_expected': triangles,
        'materials': len(material_cache),
    }


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    with open(args.spec, encoding='utf-8') as handle:
        spec = json.load(handle)
    os.makedirs(args.out, exist_ok=True)
    report = {'blender': bpy.app.version_string, 'spec': os.path.abspath(args.spec), 'assets': []}
    for asset in spec['assets']:
        report['assets'].append(export_asset(asset, args.out))
    with open(os.path.join(args.out, 'build-report.json'), 'w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print('BUILD_BOX_ASSETS_OK', json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
