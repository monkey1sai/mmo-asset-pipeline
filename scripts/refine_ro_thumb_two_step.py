"""v002: evaluate two documented plateau seeds plus a bounded second rotation."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_hand_gate import segment_hit
from ro_review_common import camera,material
BASE=ROOT/'runs/qa/ro-swordsman-combo-r007';QA=BASE/'v002-two-step';OUT=ROOT/'assets/processed/ro-swordsman-combo-r007/v002-two-step'
start=json.loads((BASE/'v002-start.json').read_text());clock=json.loads((BASE/'phase-start.json').read_text())
probe=json.loads((ROOT/start['joint_probe']['path']).read_text());source=ROOT/start['source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not QA.exists() and not OUT.exists()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior']; original=bmesh.new();original.from_mesh(ob.data)
original.verts.ensure_lookup_table();original.verts.index_update()
bands=[(Vector(x['center']),Vector(x['axis']),x['half_axial_m'],x['radius_m']) for x in probe['thumb_flex_band_parameters']]
QA.mkdir();OUT.mkdir(parents=True);events=[];best=None

def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']

def bad(bm):
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    return [v.index for v in bm.verts if len(v.link_edges)!=4 and any(abs((v.co-c).dot(d))<=a and
        ((v.co-c)-d*(v.co-c).dot(d)).length<=r for c,d,a,r in bands)]

def key(f):return tuple(sorted(v.index for v in f.verts))
def uvmap(bm):
    bm.verts.index_update();layer=bm.loops.layers.uv.active
    return {key(f):{l.vert.index:tuple(l[layer].uv) for l in f.loops} for f in bm.faces}
def topo(bm):return tuple(sorted(key(f) for f in bm.faces))
original_uv=uvmap(original);original_topo=topo(original);original_bad=bad(original)
original_poles={v.index for v in original.verts if len(v.link_edges)!=4}
def actual_triangles(bm):
    bm.verts.index_update()
    temporary=bpy.data.meshes.new('TwoStepActualLoopTriangles')
    bm.to_mesh(temporary);temporary.calc_loop_triangles()
    assert len(temporary.vertices)==len(bm.verts)
    assert all((v.co-b.co).length<1e-9 for v,b in zip(temporary.vertices,bm.verts))
    result=[tuple(t.vertices) for t in temporary.loop_triangles]
    bpy.data.meshes.remove(temporary)
    return result
old_triangles=actual_triangles(original)
original_points=[v.co.copy() for v in original.verts]
reference=BVHTree.FromPolygons(original_points,old_triangles,all_triangles=True)

def rotate(bm,edge_key,ccw):
    bm.verts.ensure_lookup_table();bm.verts.index_update()
    e=next(e for e in bm.edges if tuple(sorted(v.index for v in e.verts))==tuple(edge_key))
    assert len(e.link_faces)==2 and all(len(f.verts)==4 for f in e.link_faces)
    layer=bm.loops.layers.uv.active;local={}
    for f in e.link_faces:
        for l in f.loops:
            value=tuple(l[layer].uv)
            if l.vert.index in local:assert (Vector(local[l.vert.index])-Vector(value)).length<1e-6
            local[l.vert.index]=value
    before=uvmap(bm);bmesh.ops.rotate_edges(bm,edges=[e],use_ccw=ccw)
    bm.verts.index_update();bm.normal_update()
    changed=[f for f in bm.faces if key(f) not in before]
    assert len(changed)==2 and all(len(f.verts)==4 for f in changed)
    for f in changed:
        for l in f.loops:l[layer].uv=local[l.vert.index]

def surface_and_geometry(bm):
    bm.verts.index_update();bm.normal_update()
    ts=actual_triangles(bm)
    tree=BVHTree.FromPolygons(original_points,ts,all_triangles=True)
    changed=[f for f in bm.faces if key(f) not in original_uv]
    samples=[]
    for f in changed:
        samples.append(sum((v.co for v in f.verts),Vector())/len(f.verts))
        for l in f.loops:
            samples.extend([l.vert.co,(l.vert.co+l.link_loop_next.vert.co)/2])
    old_removed=[f for f in original.faces if key(f) not in set(key(x) for x in bm.faces)]
    old_samples=[]
    for f in old_removed:
        old_samples.append(sum((v.co for v in f.verts),Vector())/len(f.verts))
        for l in f.loops:old_samples.extend([l.vert.co,(l.vert.co+l.link_loop_next.vert.co)/2])
    residual=max([reference.find_nearest(p)[3] for p in samples]+[tree.find_nearest(p)[3] for p in old_samples]+[0])
    degenerate=0;wrong_normal=0
    for f in changed:
        nearest=reference.find_nearest(sum((v.co for v in f.verts),Vector())/len(f.verts))
        if nearest[1].dot(f.normal)<=0:wrong_normal+=1
    for a,b,c in ts:
        if (original_points[b]-original_points[a]).cross(original_points[c]-original_points[a]).length<1e-12:degenerate+=1
    crossings=[]
    for i,j in tree.overlap(tree):
        if i>=j or set(ts[i])&set(ts[j]):continue
        a=[original_points[k] for k in ts[i]];b=[original_points[k] for k in ts[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(a,b),(b,a)] for k in range(3)):
            crossings.append([i,j])
    current=uvmap(bm);preserved=[k for k in original_uv if k in current]
    uv_pass=all(all((Vector(value)-Vector(current[k][v])).length<1e-7 for v,value in original_uv[k].items()) for k in preserved)
    ip,axis,half_axial,radius=bands[2];cap_poles=[];wrong_destination=[]
    for v in bm.verts:
        if len(v.link_edges)==4 or v.index in original_poles and v.index not in original_bad:continue
        along=(v.co-ip).dot(axis)
        radial=((v.co-ip)-axis*along).length
        cap_poles.append({'vertex':v.index,'valence':len(v.link_edges),'IP_axial_m':along,'IP_radial_m':radial})
        if along<half_axial+start['cap_margin_m'] or radial>radius*1.5:wrong_destination.append(v.index)
    boundary=[e for e in bm.edges if e.is_boundary]
    manifold=all(e.is_manifold or e.is_boundary for e in bm.edges)
    return {'sampled_bidirectional_surface_max_m':residual,'surface_sample_count':len(samples)+len(old_samples),
        'degenerate_triangles':degenerate,'changed_faces_wrong_normal':wrong_normal,'neutral_transverse_pairs':len(crossings),
        'boundary_edges':len(boundary),'boundary_degree2':all(sum(e.is_boundary for e in v.link_edges)==2 for e in boundary for v in e.verts),
        'manifold_except_cuff':manifold,'actual_corner_UV_pass':uv_pass,'unchanged_faces_read_back':len(preserved),
        'new_or_moved_poles':cap_poles,'pole_wrong_destination':wrong_destination,
        'gate':residual<=start['surface_max_error_m'] and not degenerate and not wrong_normal and not crossings
            and len(boundary)==18 and manifold and uv_pass and not wrong_destination}

seen={original_topo}
for seed in start['seeds']:
    guard();first=original.copy()
    try:rotate(first,seed['edge_vertices'],seed['ccw'])
    except (AssertionError,RuntimeError,KeyError,StopIteration):first.free();continue
    first_bad=bad(first);assert len(first_bad)<=len(original_bad)
    candidates=set()
    for i in first_bad:
        for f in first.verts[i].link_faces:
            for e in f.edges:
                if len(e.link_faces)==2 and all(len(f.verts)==4 for f in e.link_faces):
                    candidates.add(tuple(sorted(v.index for v in e.verts)))
    for edge_key in sorted(candidates):
        for ccw in [False,True]:
            if len(events)>=start['maximum_second_step_probes']:break
            guard();trial=first.copy();event={'seed':seed,'second_edge':edge_key,'ccw':ccw,'event_kind':'two_step_sequence_probe'}
            try:
                rotate(trial,edge_key,ccw);fingerprint=topo(trial)
                assert fingerprint not in seen;seen.add(fingerprint)
                remaining=bad(trial);event['remaining_bad']=remaining
                if len(remaining)<len(original_bad):
                    geometry=surface_and_geometry(trial);event['geometry']=geometry
                    score=(int(not geometry['gate']),len(remaining),len(geometry['pole_wrong_destination']),geometry['sampled_bidirectional_surface_max_m'])
                    if best is None or score<best[0]:
                        if best:best[1].free()
                        best=(score,trial,event.copy());trial=None
                else:event['rejection']='no_sequence_improvement'
            except (AssertionError,RuntimeError,KeyError,StopIteration):event['rejection']='inverse_duplicate_or_UV_rotation_invalid'
            events.append(event)
            if trial is not None:trial.free()
        if len(events)>=start['maximum_second_step_probes']:break
    first.free()
    if len(events)>=start['maximum_second_step_probes']:break
candidate=best[1] if best else original.copy();remaining=bad(candidate);geometry=surface_and_geometry(candidate)
uv_actual=uvmap(candidate)
assert all((v.co-p).length<1e-9 for v,p in zip(candidate.verts,original_points))
candidate.to_mesh(ob.data);candidate.free();original.free();ob.data.update()
for v,item in zip(ob.data.vertices,ob.data.attributes['r007_original_point_id'].data):item.value=v.index
artifact=OUT/'right_hand_two_step.blend';bpy.ops.wm.save_as_mainfile(filepath=str(artifact))
gray=material('TwoStepGray',(.55,.55,.55));wire=material('TwoStepWire',(.005,.007,.009))
ob.data.materials.clear();ob.data.materials.append(gray);ob.data.materials.append(wire)
for f in ob.data.polygons:f.material_index=0
mod=ob.modifiers.new('DiagnosticWire','WIREFRAME');mod.thickness=.00028;mod.use_replace=False;mod.material_offset=1
for n,loc in {'front':(0,-1,.16),'back':(0,1,.16),'three-quarter':(.6,-1,.36)}.items():
    camera((loc,(0,0,.155),.35));bpy.context.scene.render.filepath=str(QA/(n+'.png'));bpy.ops.render.render(write_still=True)
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'initial_bad':original_bad,'final_bad':remaining,
    'sequence_probes':len(events),'maximum_second_step_probes':start['maximum_second_step_probes'],
    'best_sequence':best[2] if best else None,'actual_geometry_check':geometry,'vertex_positions_unchanged':True,
    'source_gate':not remaining and geometry['gate'],'rig_created':False,'animation_topology_accepted':False,
    'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
    'limitations':['Surface samples are discrete; no complete continuous surface equivalence proof','Neutral transverse diagnostic excludes adjacent/tangential folds','Pole-band pass would only permit small-motion testing']}
(QA/'probe-events.json').write_text(json.dumps(events,indent=2)+'\n')
(QA/'two-step.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RO_TWO_STEP '+json.dumps({'probes':len(events),'remaining':remaining,'source_gate':report['source_gate'],'geometry':geometry}))
