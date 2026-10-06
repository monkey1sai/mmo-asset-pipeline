"""Read-only source section measurements; writes only the new phase QA report."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_hand_gate import evaluated
QA = ROOT / 'runs/qa/ro-swordsman-combo-r007'
out = QA / 'assembly-measurements.json'
assert not out.exists()
start = json.loads((QA / 'preparation-start.json').read_text(encoding='utf-8'))
source = ROOT / start['baseline_source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest() == start['baseline_source']['sha256']
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
rig = bpy.data.objects['ARM_RO_Swordsman']
rig.animation_data_clear()
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
        for key in list(ob.data.shape_keys.key_blocks)[1:]:
            key.value = 0
bpy.context.view_layer.update()
wrist = rig.matrix_world @ rig.data.bones['hand.R'].head_local
elbow = rig.matrix_world @ rig.data.bones['lower_arm.R'].head_local
axis = (wrist - elbow).normalized()
state = json.loads(rig['state_json'])
width = Vector(state['hand_frames']['R']['width'])
u = (width - axis * width.dot(axis)).normalized()
v = axis.cross(u)


def sections(ob):
    p, t, edges = evaluated(ob)
    rows = []
    for axial in [-.12, -.10, -.08, -.06, -.04, -.02, 0]:
        plane = wrist + axis * axial
        coords = []
        for i, j in edges:
            a, b = p[i], p[j]
            da, db = (a - plane).dot(axis), (b - plane).dot(axis)
            if da * db < 0 and abs(da - db) > 1e-12:
                hit = a.lerp(b, da / (da - db))
                d = hit - plane
                if d.length < .12:
                    coords.append((d.dot(u), d.dot(v)))
        rows.append({'axial_from_wrist_m': axial, 'section_points': len(coords),
                     'width_range_m': [min(x for x,y in coords), max(x for x,y in coords)] if coords else None,
                     'depth_range_m': [min(y for x,y in coords), max(y for x,y in coords)] if coords else None,
                     'radial_range_m': [min((x*x+y*y)**.5 for x,y in coords), max((x*x+y*y)**.5 for x,y in coords)] if coords else None,
                     'points_width_depth_m': coords})
    return rows


bracer = bpy.data.objects['SM_RO_bracer.R']
bp, bt, _ = evaluated(bracer)
tree = BVHTree.FromPolygons(bp, bt, all_triangles=True)
import math
cavity = []
for axial in [-.12, -.10, -.08, -.06, -.04, -.02]:
    origin = wrist + axis * axial
    rays = []
    for i in range(24):
        angle = i * math.tau / 24
        d = u * math.cos(angle) + v * math.sin(angle)
        current = origin.copy()
        distances = []
        traveled = 0
        for _ in range(12):
            hit, normal, face, distance = tree.ray_cast(current, d, .15 - traveled)
            if hit is None:
                break
            traveled += distance
            distances.append(traveled)
            current = hit + d * 1e-6
            traveled += 1e-6
        rays.append({'angle_deg': i*15, 'radii_m': distances})
    cavity.append({'axial_m': axial, 'rays': rays,
                   'all_rays_hit': all(r['radii_m'] for r in rays),
                   'minimum_first_hit_m': min((r['radii_m'][0] for r in rays if r['radii_m']), default=None)})
triangles = sum(len(evaluated(ob)[1]) for ob in bpy.context.scene.objects if ob.type == 'MESH' and ob.name.startswith('SM_RO_'))
objects = ['SM_RO_glove.R', 'SM_RO_WristLoft.R', 'SM_RO_core', 'SM_RO_bracer.R']
result = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'tool': bpy.app.version_string,
    'source': start['baseline_source'], 'actual_neutral_basis_reset_in_memory': True, 'source_file_unchanged': True,
    'wrist_world_m': list(wrist), 'elbow_world_m': list(elbow), 'forearm_length_m': (wrist-elbow).length,
    'frame': {'axis_elbow_to_wrist': list(axis), 'width': list(u), 'depth': list(v)},
    'core_sections': sections(bpy.data.objects['SM_RO_core']), 'bracer_sections': sections(bracer),
    'bracer_radial_surface_hits': cavity,
    'radii_interpretation': 'First ray hit measures geometry surface, not certified free-space/visibility; open or multiple layers are explicit. Sections include existing core cloth/armor, not anatomical skin-only estimates.',
    'whole_character_and_sword_triangles': triangles,
    'replaceable_right_parts': {n: len(evaluated(bpy.data.objects[n])[1]) for n in objects[:2]},
    'design_dimensions_not_yet_frozen': True, 'art_acceptance': False,
}
assert hashlib.sha256(source.read_bytes()).hexdigest() == start['baseline_source']['sha256']
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'triangles': triangles, 'forearm_length_m': result['forearm_length_m'], 'right_replaceable': result['replaceable_right_parts'],
                  'cavity_min_first_hits': [r['minimum_first_hit_m'] for r in cavity], 'core_widths': [r['width_range_m'] for r in result['core_sections']]}))
