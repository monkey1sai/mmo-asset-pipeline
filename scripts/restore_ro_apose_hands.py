"""Same v001 clock: restore verified source-native hand regions, not a box mask.

The failed cloth repair is retained. Selection uses the original dominant bone
and named hand influence, with a rest-space sanity bound. Coordinates and UVs
must match before any weight is copied. No animation or acceptance is implied.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import camera, render_views
out = ROOT / 'assets/processed/ro-swordsman-combo-r003/v001'
qa = ROOT / 'runs/qa/ro-swordsman-combo-r003/v001'
target = out / 'ro_swordsman_hands_restored.blend'
assert not target.exists(), 'Preserve previous repair; no overwrite'
old = out / 'ro_swordsman_preflight.blend'
refined = out / 'ro_swordsman_refined_preflight.blend'
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [old, refined]}
bpy.ops.wm.open_mainfile(filepath=str(refined), load_ui=False, use_scripts=False)
body = bpy.data.objects['SM_RO_SourcePreservedBody']
rig = bpy.data.objects['ARM_RO_Swordsman']; arm = rig.data; scene = bpy.context.scene
with bpy.data.libraries.load(str(old), link=False) as (source, loaded):
    loaded.objects = ['SM_RO_SourcePreservedBody']
native = loaded.objects[0]
assert len(native.data.vertices) == len(body.data.vertices)
assert all((a.co-b.co).length < 1e-8 for a, b in zip(native.data.vertices, body.data.vertices))
old_uv = [tuple(v.uv) for v in body.data.uv_layers.active.data]
coords = [tuple(v.co) for v in body.data.vertices]
tree = ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST = {b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones}
PARENTS = {b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]), '<reviewed v001 pose functions>', 'exec'), globals())
selected = []; changed = []; rejected = []
for a, b in zip(native.data.vertices, body.data.vertices):
    weights = {native.vertex_groups[g.group].name:g.weight for g in a.groups if g.weight > 1e-8}
    dominant = max(weights, key=weights.get)
    hand = sum(w for n,w in weights.items() if n.startswith(('hand.','finger','thumb.')))
    if not dominant.startswith(('hand.','finger','thumb.')) or hand < .5:
        continue
    # Sanity assertion only: selection comes from original named bone weights.
    # Failing this assertion stops instead of widening a numerical envelope.
    if not (abs(a.co.x) > .30 and .68 < a.co.z < 1.02):
        rejected.append(a.index); continue
    selected.append(a.index)
    current = {body.vertex_groups[g.group].name:g.weight for g in b.groups if g.weight > 1e-8}
    if current != weights:
        assign(b, weights); changed.append(b.index)
assert not rejected, ('Unexpected native hand region', rejected)
assert {41,119}.issubset(changed), 'Diagnosed thumb endpoints must be restored'
assert coords == [tuple(v.co) for v in body.data.vertices]
assert old_uv == [tuple(v.uv) for v in body.data.uv_layers.active.data]
bpy.data.objects.remove(native, do_unlink=True)
poses = [('overhead',.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98)),
         ('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75)),
         ('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6))]
stats = []
scene.render.resolution_x = scene.render.resolution_y = 960
for frame, (name,h,rh,lh,sd) in enumerate(poses, 1):
    pose(frame,h,rh,lh,sd)
    ob = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = ob.to_mesh()
    edges = []
    for e in body.data.edges:
        i,j = e.vertices; old_length = (body.data.vertices[i].co-body.data.vertices[j].co).length
        new_length = (mesh.vertices[i].co-mesh.vertices[j].co).length
        if old_length > 1e-6 and new_length > .1 and new_length/old_length > 8:
            edges.append({'edge':e.index,'indices':[i,j],'ratio':new_length/old_length,'length_m':new_length})
    tracked = []
    for i,j in [(41,42),(119,9677)]:
        tracked.append({'indices':[i,j], 'length_m':(mesh.vertices[i].co-mesh.vertices[j].co).length,
                        'ratio':(mesh.vertices[i].co-mesh.vertices[j].co).length/(body.data.vertices[i].co-body.data.vertices[j].co).length})
    stats.append({'pose':name,'edges_over8x_and100mm':len(edges), 'largest':sorted(edges,key=lambda x:-x['ratio'])[:10], 'tracked':tracked})
    ob.to_mesh_clear()
    folder = qa/'preflight-hands-restored'/name; folder.mkdir(parents=True,exist_ok=False)
    for view in ['front','side','back','three-quarter']:
        camera(view); scene.render.filepath = str(folder/(view+'.png')); bpy.ops.render.render(write_still=True)
pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95))
render_views(qa/'hands-restored-views');camera()
bpy.ops.wm.save_as_mainfile(filepath=str(target))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects: ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(target.with_suffix('.glb')),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
assert before == {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [old,refined]}
report = {'same_trial':'v001','started_utc':json.loads((qa.parent/'v001-start.json').read_text())['started_utc'],
          'source_hashes':before,'selection':'Original dominant hand/thumb/finger bone with >=50% total hand influence; rest sanity assertion, not a box replacement.',
          'selected_vertices':len(selected),'restored_vertices':len(changed),'restored_indices':changed,'coordinates_unchanged':True,'UV_unchanged':True,
          'stress_diagnostics':stats,'diagnostic_threshold_is_not_acceptance':True,'full_animation':False,'acceptance':'Await independent preflight; cloth defects remain a separate gate.'}
(qa/'hand-region-restoration.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='restored_indices'}))
