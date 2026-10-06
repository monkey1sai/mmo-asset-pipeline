"""Read-only import/render inspection of a completed reference-generated GLB.

Run in an empty Blender process with --disable-autoexec and --python-exit-code 1.
Never edits the downloaded master or declares art/rig acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--label', default='rodin-v001-static')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source = Path(args.input).resolve(strict=True)
if ROOT not in source.parents or source.suffix.lower() != '.glb':
    raise ValueError('Input must be an actual GLB within this worktree')
qa = ROOT / 'runs' / 'qa' / 'ro-swordsman-combo' / args.label
qa.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
objects = list(bpy.context.scene.objects)
meshes = [o for o in objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
stats = []
for o in meshes:
    bm = bmesh.new(); bm.from_mesh(o.data)
    remaining = set(bm.verts); sizes = []
    while remaining:
        stack = [remaining.pop()]; size = 0
        while stack:
            v = stack.pop(); size += 1
            for e in v.link_edges:
                n = e.other_vert(v)
                if n in remaining:
                    remaining.remove(n); stack.append(n)
        sizes.append(size)
    stats.append({'name': o.name, 'vertices': len(o.data.vertices),
                  'triangles': sum(len(p.vertices)-2 for p in o.data.polygons),
                  'materials': [m.name if m else None for m in o.data.materials],
                  'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                  'components': sorted(sizes, reverse=True),
                  'vertex_groups': len(o.vertex_groups),
                  'modifiers': [m.type for m in o.modifiers]})
    bm.free()
report = {'source': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'tool': bpy.app.version_string, 'import_bounds_m': {'min': list(minimum), 'max': list(maximum)},
          'objects': stats, 'armatures': [o.name for o in objects if o.type == 'ARMATURE'],
          'images': [{'name': i.name, 'size': list(i.size), 'packed': bool(i.packed_file)} for i in bpy.data.images if i.type == 'IMAGE'],
          'acceptance': 'not_run', 'normalization': 'Preview only: center XY, ground Z, scale height to 1.74m; downloaded bytes unchanged'}
height = maximum.z - minimum.z
if height <= 0:
    raise ValueError('No positive-height character geometry')
parent = bpy.data.objects.new('PreviewNormalization', None)
bpy.context.scene.collection.objects.link(parent)
for o in objects:
    if o.parent is None:
        matrix = o.matrix_world.copy(); o.parent = parent; o.matrix_world = matrix
parent.scale = (1.74/height,)*3
parent.location = Vector((-(maximum.x+minimum.x)/2, -(maximum.y+minimum.y)/2, -minimum.z)) * (1.74/height)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.world.color = (.16,.16,.16)
scene.eevee.taa_render_samples = 64
bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
m = bpy.data.materials.new('ReviewFloor'); m.use_nodes = True
p = m.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value = (.18,.19,.21,1)
p.inputs['Roughness'].default_value = .9
floor.data.materials.append(m)
for name,loc,power,size in [('Key',(3,-4,5),700,4),('Fill',(-3,-2,3),350,3),('Rim',(0,3,4),800,3)]:
    d = bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o = bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc
    o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('ReviewCamera'); cam=bpy.data.objects.new('ReviewCamera',d)
scene.collection.objects.link(cam); d.type='ORTHO'; scene.camera=cam
views={'front':((0,-4,1.35),(0,0,.9),2.25),'side':((4,0,1.35),(0,0,.9),2.25),
       'back':((0,4,1.35),(0,0,.9),2.25),'three-quarter':((2.8,-4,2),(0,0,.9),2.25),
       'detail':((1.2,-4,1.75),(0,0,1.53),.62)}
for name,(loc,target,scale) in views.items():
    cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); d.ortho_scale=scale
    scene.render.filepath=str(qa/(name+'.png')); bpy.ops.render.render(write_still=True)
(qa/'static-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STATIC_INSPECTION '+json.dumps(report))
