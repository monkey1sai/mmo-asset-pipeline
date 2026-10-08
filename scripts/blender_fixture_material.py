"""Explicit glTF-compatible material for local engineering fixtures."""
import math


def make_fixture_material(bpy, name, color):
    if len(color) != 4 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in color):
        raise ValueError('INVALID_LINEAR_RGBA')
    material = bpy.data.materials.new(name)
    material.diffuse_color = tuple(color)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = tuple(color)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .5
    shader.inputs['Alpha'].default_value = color[3]
    return material
