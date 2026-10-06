"""Bounded native-quad edge rotations with frozen joint bands and UV readback."""
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
import sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'scripts'))
from ro_review_common import camera, material
BASE = ROOT/'runs/qa/ro-swordsman-combo-r007'; QA=BASE/'v001-thumb-flow'
OUT=ROOT/'assets/processed/ro-swordsman-combo-r007/v001-thumb-flow'
assert not QA.exists() and not OUT.exists()
probe=json.loads((BASE/'v001-source-preparation/joint-and-pole-probe.json').read_text())
source=ROOT/probe['source']['path']; assert hashlib.sha256(source.read_bytes()).hexdigest()==probe['source']['sha256']
clock=json.loads((BASE/'phase-start.json').read_text()); start=json.loads((BASE/'v001-start.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior']; bm=bmesh.new(); bm.from_mesh(ob.data)
bands=[(Vector(r['center']),Vector(r['axis']),r['half_axial_m'],r['radius_m']) for r in probe['thumb_flex_band_parameters']]
QA.mkdir(); OUT.mkdir(parents=True)
events=[]; chosen=[]; MAX_PROBES=160; MAX_ROTATIONS=8

def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']

def bad(mesh):
    mesh.verts.ensure_lookup_table(); mesh.verts.index_update()
    return [v.index for v in mesh.verts if len(v.link_edges)!=4 and any(
        abs((v.co-c).dot(d))<=a and ((v.co-c)-d*(v.co-c).dot(d)).length<=r for c,d,a,r in bands)]

def face_key(f): return tuple(sorted(v.index for v in f.verts))

def uv_snapshot(mesh):
    mesh.verts.index_update(); layer=mesh.loops.layers.uv.active
    return {face_key(f):{l.vert.index:tuple(l[layer].uv) for l in f.loops} for f in mesh.faces}

def tree_for(mesh):
    mesh.verts.index_update()
    return BVHTree.FromPolygons([v.co for v in mesh.verts],[[v.index for v in f.verts] for f in mesh.faces])

initial_uv=uv_snapshot(bm); original_points=[v.co.copy() for v in bm.verts]
initial_bad=bad(bm); stop_reason='not_started'
for iteration in range(MAX_ROTATIONS):
    guard(); defects=bad(bm)
    if not defects: stop_reason='frozen_thumb_bands_clear'; break
    baseline_uv=uv_snapshot(bm); baseline_tree=tree_for(bm)
    keys=set()
    for index in defects:
        v=bm.verts[index]
        for f in v.link_faces:
            for e in f.edges:
                if len(e.link_faces)==2 and all(len(f.verts)==4 for f in e.link_faces):
                    keys.add(tuple(sorted(x.index for x in e.verts)))
    best=None
    for edge_key in sorted(keys):
        for ccw in [False,True]:
            if len(events)>=MAX_PROBES: break
            guard(); trial=bm.copy(); trial.verts.ensure_lookup_table(); trial.verts.index_update(); trial.edges.ensure_lookup_table()
            edge=next(e for e in trial.edges if tuple(sorted(v.index for v in e.verts))==edge_key)
            affected=[f for f in edge.link_faces]; local_uv={}; ambiguous=False
            layer=trial.loops.layers.uv.active
            for f in affected:
                for l in f.loops:
                    value=tuple(l[layer].uv)
                    if l.vert.index in local_uv and (Vector(local_uv[l.vert.index])-Vector(value)).length>1e-6:
                        ambiguous=True
                    local_uv[l.vert.index]=value
            event={'iteration':iteration,'edge_vertices':edge_key,'ccw':ccw,'before_bad':len(defects),
                   'event_kind':'topology_probe','observed_utc':datetime.now(timezone.utc).isoformat()}
            if ambiguous:
                event['rejection']='UV_seam_ambiguity'; events.append(event); trial.free(); continue
            try:
                bmesh.ops.rotate_edges(trial,edges=[edge],use_ccw=ccw)
                trial.verts.index_update(); trial.faces.ensure_lookup_table(); trial.normal_update()
                after_keys={face_key(f) for f in trial.faces}; changed=[f for f in trial.faces if face_key(f) not in baseline_uv]
                assert len(changed)==2 and all(len(f.verts)==4 for f in changed)
                for f in changed:
                    for l in f.loops: l[layer].uv=local_uv[l.vert.index]
                residual=max(baseline_tree.find_nearest(sum((v.co for v in f.verts),Vector())/len(f.verts))[3] for f in changed)
                remaining=bad(trial)
                event.update(after_bad=len(remaining),surface_centroid_residual_m=residual,
                             changed_faces=[list(face_key(f)) for f in changed])
                if len(remaining)<len(defects) and residual<=.0015:
                    score=(len(remaining),residual)
                    if best is None or score<best[0]:
                        if best: best[1].free()
                        best=(score,trial,event.copy()); trial=None
                else: event['rejection']='no_pole_reduction_or_surface_residual'
            except (RuntimeError,AssertionError,KeyError,ValueError):
                event['rejection']='rotation_or_UV_contract_invalid'
            events.append(event)
            if trial is not None: trial.free()
        if len(events)>=MAX_PROBES: break
    (QA/'probe-events.json').write_text(json.dumps(events,indent=2)+'\n')
    if best is None:
        stop_reason='no_legal_improving_local_rotation'; break
    bm.free(); bm=best[1]; chosen.append(best[2])
    if len(events)>=MAX_PROBES:
        stop_reason='probe_budget_used'; break
final_bad=bad(bm); current_uv=uv_snapshot(bm)
preserved=[key for key in initial_uv if key in current_uv]
assert all(all((Vector(value)-Vector(current_uv[key][vertex])).length<1e-7 for vertex,value in initial_uv[key].items()) for key in preserved)
assert all((v.co-p).length<1e-9 for v,p in zip(bm.verts,original_points))
bm.to_mesh(ob.data); bm.free(); ob.data.update()
tag=ob.data.attributes['r007_original_point_id']
for v,item in zip(ob.data.vertices,tag.data): item.value=v.index
artifact=OUT/'right_hand_thumb_flow.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(artifact))
gray=material('ThumbFlowGray',(.55,.55,.55)); wire=material('ThumbFlowWire',(.005,.007,.009))
ob.data.materials.clear(); ob.data.materials.append(gray); ob.data.materials.append(wire)
for f in ob.data.polygons: f.material_index=0
mod=ob.modifiers.new('DiagnosticWire','WIREFRAME'); mod.thickness=.00028; mod.use_replace=False; mod.material_offset=1
for name,loc in {'front':(0,-1,.16),'back':(0,1,.16),'three-quarter':(.6,-1,.36)}.items():
    camera((loc,(0,0,.155),.35)); bpy.context.scene.render.filepath=str(QA/(name+'.png')); bpy.ops.render.render(write_still=True)
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':probe['source'],
    'frozen_joint_probe':{'path':(BASE/'v001-source-preparation/joint-and-pole-probe.json').relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256((BASE/'v001-source-preparation/joint-and-pole-probe.json').read_bytes()).hexdigest()},
    'initial_bad_poles':initial_bad,'final_bad_poles':final_bad,'pole_gate':not final_bad,
    'probe_count':len(events),'maximum_probes':MAX_PROBES,'maximum_rotations':MAX_ROTATIONS,
    'chosen_rotations':chosen,'stop_reason':stop_reason,'vertex_positions_unchanged':True,
    'unchanged_face_count_UV_readback':len(preserved),'changed_original_face_count':len(initial_uv)-len(preserved),
    'untouched_corner_UV_pass':True,'changed_face_UV_method':'Existing consistent local vertex UV; seams rejected',
    'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==probe['source']['sha256'],
    'rig_created':False,'animation_topology_accepted':False,
    'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
    'limitations':['Centroid surface residual is partial; actual changed triangles/self-intersections still require validation before binding',
                   'Frozen joint bands are a bounded artist mask, not all possible deformation regions']}
(QA/'flow.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RO_THUMB_FLOW '+json.dumps({'before':len(initial_bad),'after':len(final_bad),'probes':len(events),'rotations':len(chosen),'stop_reason':stop_reason}))
