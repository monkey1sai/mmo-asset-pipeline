"""Compose existing component inspection with original-ID review; never repair."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import colorsys
import json
from pathlib import Path
import sys
import time
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity
import art_sources
from inspect_ro_batch_source import components
ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    for name in ('blend', 'sha256', 'mesh', 'out'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = identity.command_path(ROOT, a.blend)
    if identity.file_digest(source) != a.sha256:
        raise ValueError('BASELINE_DRIFT')
    relative = identity.command_path(ROOT, a.out).relative_to(ROOT).as_posix()
    art_sources.safe_relative(relative)
    if not relative.startswith('runs/qa/'):
        raise ValueError('OUTPUT_SCOPE')
    out = art_sources.no_symlinks(ROOT, relative)
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    obj = bpy.data.objects.get(a.mesh)
    if obj is None or obj.type != 'MESH':
        raise ValueError('MESH_REQUIRED')
    attr = obj.data.attributes.get('original_gltf_vertex_id')
    if attr is None:
        raise ValueError('ORIGINAL_IDS_REQUIRED')
    ids = [d.value for d in attr.data]
    if sorted(ids) != list(range(len(obj.data.vertices))):
        raise ValueError('ORIGINAL_ID_PERMUTATION')
    # Exact topological components: no positional welding or weight inference.
    adjacency = [set() for _ in ids]
    for edge in obj.data.edges:
        x, y = edge.vertices
        adjacency[x].add(y)
        adjacency[y].add(x)
    labels = [-1] * len(ids)
    groups = []
    for seed in range(len(ids)):
        if labels[seed] >= 0:
            continue
        todo = [seed]
        group = []
        labels[seed] = len(groups)
        while todo:
            x = todo.pop()
            group.append(x)
            for y in adjacency[x]:
                if labels[y] < 0:
                    labels[y] = len(groups)
                    todo.append(y)
        groups.append(group)
    faces = defaultdict(list)
    for face in obj.data.polygons:
        cats = {labels[v] for v in face.vertices}
        if len(cats) != 1:
            raise ValueError('FACE_COMPONENT_MISMATCH')
        faces[cats.pop()].append(face.index)
    exact = []
    for ci, group in enumerate(groups):
        points = [obj.matrix_world @ obj.data.vertices[v].co for v in group]
        exact.append({'id': ci, 'vertices': len(group), 'triangles': len(faces[ci]),
            'original_vertex_ids': sorted(ids[v] for v in group), 'imported_polygon_indices': faces[ci],
            'world_min': [min(v[k] for v in points) for k in range(3)],
            'world_max': [max(v[k] for v in points) for k in range(3)]})
    exact.sort(key=lambda x: (-x['triangles'], x['id']))
    # Reuse existing 1e-6 mesh-local quantized logical weld, separately reported. It may
    # merge touching disconnected surfaces; it is not an anatomical partition.
    welded = components(obj.data)
    for c in welded:
        c['original_vertex_ids'] = sorted({ids[v] for tid in c['polygon_indices'] for v in obj.data.polygons[tid].vertices})
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = True
    review = obj.copy()
    review.data = obj.data.copy()
    review.name = 'REVIEW_ONLY-geometric-components'
    bpy.context.scene.collection.objects.link(review)
    review.hide_render = False
    review.data.materials.clear()
    for c in welded:
        color = colorsys.hsv_to_rgb((c['id'] * .61803398875) % 1, .75, .8)
        m = bpy.data.materials.new('REVIEW_COMPONENT_' + str(c['id']))
        m.use_nodes = True
        m.diffuse_color = (*color, 1)
        m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*color, 1)
        review.data.materials.append(m)
        for tid in c['polygon_indices']:
            review.data.polygons[tid].material_index = c['id']
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    camera_data = bpy.data.cameras.new('ComponentCamera')
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 2.6
    camera = bpy.data.objects.new('ComponentCamera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, loc, power, size in [('Key', (3,-4,5),1100,5), ('Fill',(-3,2,3),700,4)]:
        data = bpy.data.lights.new('Component' + name, 'AREA')
        data.energy = power
        data.size = size
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = loc
        light.rotation_euler = (Vector((0,0,1)) - light.location).to_track_quat('-Z','Y').to_euler()
    scene.world.color = (.12,.12,.12)
    for name, loc in [('front',(0,-5,1.25)), ('back',(0,5,1.25)), ('side',(5,0,1.25))]:
        camera.location = loc
        camera.rotation_euler = (Vector((0,0,1)) - camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath = str(out / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'component-review.blend'))
    report = {'baseline_sha256': a.sha256, 'baseline_unchanged': identity.file_digest(source) == a.sha256,
        'blender': bpy.app.version_string, 'mesh': a.mesh, 'exact_components': exact,
        'logical_weld_components': welded, 'logical_weld_quantization_mesh_local': 1e-6,
        'scene_unit_scale': scene.unit_settings.scale_length,
        'mesh_world_matrix': [list(row) for row in obj.matrix_world],
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds': time.monotonic() - clock, 'model_revision': False,
        'semantic_mask_status': 'NOT_ACCEPTED',
        'limitations': 'Connectivity is not anatomy. Logical quantization is mesh-local, not a guaranteed metric distance, and can merge touching surfaces. Polygon indices are Blender import indices, not original glTF triangle IDs. Original vertex IDs are explicit. Colors are presentation on a copied mesh; original material/UV/weights preserved.'}
    with (out / 'report.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'exact': len(exact), 'logical_weld': len(welded), 'unchanged': report['baseline_unchanged']}))

if __name__ == '__main__':
    main()
