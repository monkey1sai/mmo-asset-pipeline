"""Actual saved-clip frame and half-frame baseline checks; no search or mesh saves."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_hand_gate import contacts,segment_hit
QA=ROOT/'runs/qa/ro-swordsman-combo-r007'; out=QA/'baseline/baked-interval.json'; assert not out.exists()
source=ROOT/'assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; tube=bpy.data.objects['SM_RO_WristLoft.R']; sword=bpy.data.objects['SM_RO_sword']
pads=json.loads(glove['fixed_pad_indices']); canonical={}
for ob in [glove,tube]:
    tag=ob.data.attributes.new('r007_original_point_id','INT','POINT'); seen={}; ids=[]
    for vertex,item in zip(ob.data.vertices,tag.data):
        item.value=vertex.index; key=tuple(round(float(x),6) for x in vertex.co); ids.append(seen.setdefault(key,vertex.index))
    canonical[ob.name]=ids
def self_count(ob):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh(); mesh.calc_loop_triangles()
    assert [r.value for r in mesh.attributes['r007_original_point_id'].data]==list(range(len(ob.data.vertices)))
    p=[ev.matrix_world@v.co for v in mesh.vertices]; ts=[tuple(t.vertices) for t in mesh.loop_triangles]; ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(p,ts,all_triangles=True); count=0
    for i,j in tree.overlap(tree):
        if i>=j or {canonical[ob.name][v] for v in ts[i]}&{canonical[ob.name][v] for v in ts[j]}: continue
        a=[p[v] for v in ts[i]]; b=[p[v] for v in ts[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(a,b),(b,a)] for k in range(3)): count+=1
    return count
rows=[]
for sample in range(121):
    frame=1+sample*.5
    bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame)); bpy.context.view_layer.update()
    c=contacts(glove,sword,rig,pads,'baked-interval-baseline',{'frame':frame,'source_byte_unchanged':True,'search':False})
    row={'frame':frame,'kind':'actual_baked_frame' if frame.is_integer() else 'half_frame_diagnostic',
        'holding_interval_contact_required':frame==61,'maximum_penetration_m':c['maximum_penetration_m'],
        'sword_transverse_pairs':c['transverse_crossings_count'],'inside_unknown_samples':len(c['unknown_inside']),
        'contact_pads':c['pad_contacts'],'glove_transverse_self_pairs':self_count(glove),'wrist_transverse_self_pairs':self_count(tube),
        'geometry_fingerprint':c['candidate_fingerprint']}
    rows.append(row)
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':{'path':source.relative_to(ROOT).as_posix(),'sha256':digest},
    'local_contract':{'path':(QA/'hand-gate-contract-v2.json').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((QA/'hand-gate-contract-v2.json').read_bytes()).hexdigest()},
    'frames':61,'half_frame_diagnostics':60,'samples':rows,'search_evaluations':0,'new_geometry_versions':0,
    'baked_interval_collision_pass':all(r['maximum_penetration_m']<=.001 and not r['sword_transverse_pairs'] and not r['inside_unknown_samples'] for r in rows),
    'baked_interval_art_pass':False,'limitations':['Discrete61frames+60half-frame diagnostics are not continuous collision proof','Same evaluated point+loop triangles with original-point attribute identity; adjacency is frozen at rest','Transverse tests exclude coplanar/tangential/adjacent folds; actual close views remain required'],
    'original_source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==digest,'producer_no_file_saved':True}
with out.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps({'samples':len(rows),'actual_frames':61,'half_frames':60,'collision_pass':result['baked_interval_collision_pass'],
    'maximum_depth_mm':max(r['maximum_penetration_m'] for r in rows)*1000,'sword_crossing_samples':sum(r['sword_transverse_pairs']>0 for r in rows),'art':'NO_SHIP'}))
