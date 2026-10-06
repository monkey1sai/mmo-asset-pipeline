"""Baseline anatomy and bad-edge positions BEFORE freezing any new anchors."""
from datetime import datetime, timezone
import hashlib
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from ro_weight_vector_common import *

clock = read(QA/'phase-start.json')
folder = QA/'source-probe'
assert not folder.exists()
folder.mkdir()
for entry in clock['protected_history']:
    assert artifact(ROOT/entry['path']) == entry
source = ROOT/clock['local_baseline_source']['path']
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects['SM_RO_RightHand_Exterior']
rig = bpy.data.objects['ARM_RO_HandDiagnostic']
reset(rig)
rest = geometry(ob)
before_weights = weights(ob)
with bpy.data.libraries.load(str(ROOT/clock['geometry_guide']['path']), link=False) as (src, dst):
    dst.objects = ['SM_RO_RightHand_Exterior']
guide = dst.objects[0]
guide_geometry = geometry(guide)
assert rest == guide_geometry, 'Coordinates, polygon indices, corner UVs and source IDs must match'
bpy.data.objects.remove(guide, do_unlink=True)
neighbors = {i: set() for i in range(len(rest['points']))}
for a, b in rest['edges']:
    neighbors[a].add(b)
    neighbors[b].add(a)
bad = [[56,580], [57,582], [59,578]]
bone_points = {n: {'head': list(rig.data.bones[n].head_local), 'tail': list(rig.data.bones[n].tail_local)} for n in CHAIN}
bad_rows = []
for edge in bad:
    rows = []
    for i in edge:
        p = Vector(rest['points'][i])
        joint_rows = {}
        for n in CHAIN[1:]:
            h,t = Vector(bone_points[n]['head']), Vector(bone_points[n]['tail'])
            d = (t-h).normalized()
            joint_rows[n] = {'axial_m': (p-h).dot(d), 'radial_m': (p-h-d*(p-h).dot(d)).length}
        one = neighbors[i]
        two = set().union(*(neighbors[j] for j in one)) - one - {i}
        rows.append({'point_id': i, 'source_id': rest['point_attributes']['r007_source_point_id'][i],
                     'rest_position': list(p), 'weights': before_weights[i],
                     'joint_relation': joint_rows, 'one_ring': sorted(one), 'two_ring': sorted(two)})
    bad_rows.append({'edge': edge, 'ends': rows})
save(folder/'mesh-and-weights.json', {'geometry': rest, 'weights': before_weights, 'bone_points': bone_points})
saved = list(ob.data.materials)
ob.data.materials.clear()
ob.data.materials.append(material('r008BaselineGray', (.55,.55,.55)))
events = []
neutral = None
for label, params in isolated_parameters():
    event, pts = actual(ob, rig, rest, label, params, before_weights)
    events.append(event)
    if label == 'neutral':
        neutral = pts
        render(folder, 'neutral')
    if label in ['IP-+0.30', 'MCP-+0.30', 'CMC-+0.30', 'CMC-opposition-+0.15']:
        render(folder, label, ['palm','side'])
params = combined_parameters(.30)
event, pts = actual(ob, rig, rest, 'historical-combined030', params, before_weights)
events.append(event)
render(folder, 'historical-combined030')
pose(rig, [])
points = [Vector(p) for p in rest['points']]
markers = [line_object('BadEdges', [[points[a], points[b]] for a,b in bad], (1,.08,.03), .0008),
           line_object('MeshWire', [[points[a],points[b]] for a,b in rest['edges']], (.07,.07,.07), .00012),
           line_object('ThumbJoints', [[rig.data.bones[n].head_local,rig.data.bones[n].tail_local] for n in CHAIN[1:]], (.08,.5,1), .00055)]
for section_name, row in events[0]['sections'].items():
    markers.append(line_object('Section'+section_name, row['segments'], (.1,1,.15), .00035))
render(folder, 'anatomy-overlay')
for marker in markers:
    bpy.data.objects.remove(marker, do_unlink=True)
report = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'source': clock['local_baseline_source'],
          'geometry_guide': clock['geometry_guide'], 'exact_mesh_face_UV_sourceID_equivalence': True,
          'bad_edges': bad_rows, 'events': events, 'actual_new_anchors_or_weights': False,
          'baseline_scope': 'Actual existing local failed weight specimen; isolated signed tests, not new candidate or fullcharacter improvement.',
          'known_UV_fail_faces': 16, 'whole_character_accepted': False,
          'actual_views': [artifact(p) for p in sorted(folder.glob('*.png'))]}
save(folder/'probe.json', report)
print('R008_SOURCE '+json.dumps({'vertices':len(points),'equivalence':True,'poses':len(events),
       'bad_edges':bad_rows, 'max_ratios':[(r['label'],r['maximum_edge_stretch']) for r in events]}))
