"""Actual local hand readback, shared without editing historical helpers."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from ro_hand_gate import segment_hit
from ro_review_common import camera, material

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r008'
VIEWS = {'palm': ((0, -1, .22), (.005, 0, .18), .29),
         'side': ((1, -.2, .24), (.005, 0, .18), .29),
         'back': ((0, 1, .22), (.005, 0, .18), .29)}
CHAIN = ['hand', 'thumb_01', 'thumb_02', 'thumb_03']

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def artifact(path):
    return {'path': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def geometry(ob):
    me = ob.data
    return {'points': [list(v.co) for v in me.vertices],
            'edges': [list(e.vertices) for e in me.edges],
            'faces': [list(p.vertices) for p in me.polygons],
            'uv': [[list(l.uv) for l in uv.data] for uv in me.uv_layers],
            'point_attributes': {a.name: [d.value for d in a.data]
                for a in me.attributes if a.domain == 'POINT' and a.data_type == 'INT'}}

def weights(ob):
    return {v.index: {ob.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-8}
            for v in ob.data.vertices}

def reset(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

def rotate(rig, name, angle, mode='flexion'):
    bone = rig.data.bones[name]
    native = bone.matrix_local.to_3x3()
    direction = (bone.tail_local - bone.head_local).normalized()
    # Positive flexion moves distal surface toward the palm (-Y).
    # Opposition is axial pronation of thumb metacarpal; its positive direction
    # is verified on a frozen palmar pad toward ulnar palm (-X), separately.
    axis = Vector((0, -1, 0)).cross(direction).normalized() if mode == 'flexion' else direction
    rotation = Matrix.Rotation(-angle if mode in ['flexion', 'opposition_ulnar'] else angle, 3, axis)
    pb = rig.pose.bones[name]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (native.inverted() @ rotation @ native).to_quaternion()
    bpy.context.view_layer.update()
    return list(axis)

def pose(rig, parameters):
    reset(rig)
    for row in parameters:
        rotate(rig, row['bone'], row['angle'], row.get('mode', 'flexion'))

def isolated_parameters(opposition_mode='opposition'):
    rows = [('neutral', [])]
    for joint, name in [('IP', 'thumb_03'), ('MCP', 'thumb_02'), ('CMC', 'thumb_01')]:
        for a in [-.30, -.15, -.05, .05, .15, .30]:
            rows.append((f'{joint}-{a:+.2f}', [{'bone': name, 'angle': a, 'mode': 'flexion'}]))
    for a in [-.15, -.05, .05, .15]:
        rows.append((f'CMC-opposition-{a:+.2f}', [{'bone': 'thumb_01', 'angle': a, 'mode': opposition_mode}]))
    return rows

def combined_parameters(a):
    return [{'bone': f'{branch}_{i:02}', 'angle': a * factor, 'mode': 'flexion'}
            for branch in ['finger1', 'finger2', 'finger3', 'finger4', 'thumb']
            for i, factor in [(1, 1), (2, 1.4), (3, .85)]]

def convex_area(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return 0.
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves = []
    for order in [pts, pts[::-1]]:
        part = []
        for p in order:
            while len(part) >= 2 and cross(part[-2], part[-1], p) <= 0:
                part.pop()
            part.append(p)
        halves.append(part[:-1])
    hull = halves[0]+halves[1]
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(hull, hull[1:]+hull[:1])))/2

def section(points, faces, center, axis):
    axis = axis.normalized()
    u = axis.cross(Vector((0, 1, 0))).normalized()
    v = axis.cross(u).normalized()
    segments = []
    for ids in faces:
        hits = []
        for a, b in zip(ids, ids[1:]+ids[:1]):
            da, db = (points[a]-center).dot(axis), (points[b]-center).dot(axis)
            if da*db < 0:
                p = points[a].lerp(points[b], da/(da-db))
                hits.append(p)
        if len(hits) == 2:
            segments.append(hits)
    flat = [((p-center).dot(u), (p-center).dot(v)) for seg in segments for p in seg]
    return {'center': list(center), 'axis': list(axis), 'segments': [[list(p) for p in s] for s in segments],
            'convex_enclosure_area_m2': convex_area(flat),
            'width_m': max((p[0] for p in flat), default=0)-min((p[0] for p in flat), default=0),
            'depth_m': max((p[1] for p in flat), default=0)-min((p[1] for p in flat), default=0),
            'perimeter_segments_m': sum((b-a).length for a, b in segments),
            'limitation': 'Plane intersects actual polygons; convex enclosure includes voids and cannot alone prove local volume acceptance.'}

def actual(ob, rig, rest, label, parameters, all_weights=None, crossing_limit=20):
    pose(rig, parameters)
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    mesh.calc_loop_triangles()
    assert [d.value for d in mesh.attributes['r007_original_point_id'].data] == list(range(len(rest['points'])))
    points = [v.co.copy() for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    faces = [list(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    assert faces == rest['faces']
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    crossings = []
    for i, j in tree.overlap(tree):
        if i >= j or set(triangles[i]) & set(triangles[j]):
            continue
        left, right = [points[k] for k in triangles[i]], [points[k] for k in triangles[j]]
        if any(segment_hit(a[k], a[(k+1)%3], b) is not None
               for a, b in [(left, right), (right, left)] for k in range(3)):
            crossings.append([i, j])
    edges = []
    for a, b in rest['edges']:
        length = (points[b]-points[a]).length
        base = (Vector(rest['points'][b])-Vector(rest['points'][a])).length
        row = {'edge': [a, b], 'rest_m': base, 'posed_m': length,
               'delta_m': length-base, 'ratio': length/base}
        if all_weights is not None:
            names = set(all_weights[a]) | set(all_weights[b])
            diff = [all_weights[a].get(n, 0)-all_weights[b].get(n, 0) for n in names]
            row.update(weight_L1=sum(abs(d) for d in diff), weight_L2=sum(d*d for d in diff)**.5)
        edges.append(row)
    sections = {}
    for joint, name in [('CMC', 'thumb_01'), ('MCP', 'thumb_02'), ('IP', 'thumb_03')]:
        pb = rig.pose.bones[name]
        sections[joint] = section(points, faces, pb.head.copy(), (pb.tail-pb.head).normalized())
    result = {'label': label, 'parameters': parameters, 'transverse_pairs': len(crossings),
              'crossings': crossings if crossing_limit is None else crossings[:crossing_limit],
              'degenerate_triangles': sum((points[b]-points[a]).cross(points[c]-points[a]).length < 1e-12 for a,b,c in triangles),
              'maximum_edge_stretch': max(r['ratio'] for r in edges),
              'minimum_edge_ratio': min(r['ratio'] for r in edges),
              'maximum_absolute_edge_change_m': max(abs(r['delta_m']) for r in edges),
              'worst_stretch': sorted(edges, key=lambda r: -r['ratio'])[:10],
              'worst_absolute': sorted(edges, key=lambda r: -abs(r['delta_m']))[:10],
              'sections': sections,
              'positions_sha256': hashlib.sha256(json.dumps([list(p) for p in points]).encode()).hexdigest(),
              'raw_point_identity_verified': True,
              'limitations': ['Transverse test excludes tangent/coplanar/adjacent folds; zero never means visual acceptance.',
                              'Short edge ratio inflation must be compared with absolute deformation and actual rendered silhouette.']}
    return result, points

def render(folder, label, view_names=None):
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    for name in view_names or VIEWS:
        camera(VIEWS[name])
        scene.render.filepath = str(folder / (label+'-'+name+'.png'))
        bpy.ops.render.render(write_still=True)

def line_object(name, lines, color, radius=.00025):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 0
    for points in lines:
        spline = curve.splines.new('POLY')
        spline.points.add(len(points)-1)
        for dest, p in zip(spline.points, points):
            dest.co = (*p, 1)
    ob = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material(name+'Material', color, emission=.5))
    return ob
