"""Last bounded right-hand surface test; safety violations cannot be averaged away."""
from datetime import datetime,timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign,pose
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-surface'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-surface'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-roll/roll.json').read_text()); source=ROOT/previous['artifact']['path']
if QA.exists() or OUT.exists() or hashlib.sha256(source.read_bytes()).hexdigest()!=previous['artifact']['sha256']: raise RuntimeError('Preserve surface tests and source')
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-start.json').read_text())
def guard():
    if (datetime.now(timezone.utc)-datetime.fromisoformat(start['started_utc'])).total_seconds()>=start['prototype_deadline_seconds']: raise RuntimeError('Original prototype deadline exhausted')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']; state=json.loads(rig['state_json']); original=copy.deepcopy(state)
# The full forearm roll did not improve the visible cuff; preserve/discard its trial.
state['forearm_twist_to_palm']={'R':False}
# Continuous thumb-port weights; previous diagnostic found a6.22x edge across hand1 -> thumb1.
thumb_head=Vector(state['rest']['thumb.R_01'][0]); thumb_mid=Vector(state['rest']['thumb.R_01'][1]); thumb_tip=Vector(state['rest']['thumb.R_02'][1]); thumb_axis=(thumb_tip-thumb_head).normalized()
changed=[]
for v in core.data.vertices:
    if not (v.co.x<-.46 and .878<v.co.z<.913): continue
    d=v.co-thumb_head; along=d.dot(thumb_axis); radius=(d-thumb_axis*along).length
    if -.006<along<.024 and radius<.027:
        amount=max(0,min(1,(along+.015)/.050)); assign(core,v,{'hand.R':1-amount,'thumb.R_01':amount}); changed.append(v.index)
original_sword=[v.co.copy() for v in sword.data.vertices]
frame=state['hand_frames']['R']; front=Vector(frame['front']); down=Vector(frame['down']); palm=sum((Vector(v) for v in state['measurements']['R']['knuckles']),Vector())/4
def grip(f,d):
    origin=palm+front*f+down*d; state['grips']['R']=list(origin)
    delta=origin-Vector(original['grips']['R'])
    for v,raw in zip(sword.data.vertices,original_sword): v.co=raw+delta
    sword.data.update()
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
    b=rig.data.edit_bones['sword']; b.head=origin; b.tail=origin+Vector(state['weapon_axis_in_rest'])*.8; bpy.ops.object.mode_set(mode='OBJECT')
    state['rest']['sword']=[list(origin),list(origin+Vector(state['weapon_axis_in_rest'])*.8)]
indices=[v.index for v in core.data.vertices if v.co.x<-.34 and v.co.z<.96]
face_ids=[f.index for f in core.data.polygons if all(core.data.vertices[i].co.x<-.34 and core.data.vertices[i].co.z<.923 for i in f.vertices)]
directions=[Vector((.713,.389,.587)).normalized(),Vector((.419,.831,.365)).normalized()]
def interior(tree,p,direction):
    origin=p+direction*1e-6; count=0
    for _ in range(80):
        hit,normal,index,dist=tree.ray_cast(origin,direction,4)
        if hit is None: return bool(count%2)
        count+=1; origin=hit+direction*1e-6
    raise RuntimeError('Ambiguous ray')
def evaluate(f,d,angle,thumb=None):
    guard(); grip(f,d)
    state['finger_angles']['R']={str(i):[angle,angle*1.40,angle*.85] for i in range(1,5)}
    if thumb: state['thumb_offsets']['R']=thumb
    pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),two_hands=False)
    deps=bpy.context.evaluated_depsgraph_get(); ev=core.evaluated_get(deps); weapon=sword.evaluated_get(deps)
    pts=[weapon.matrix_world@v.co for v in weapon.data.vertices]; solid=BVHTree.FromPolygons(pts,[list(f.vertices) for f in weapon.data.polygons]); center=rig.pose.bones['sword'].head; axis=(rig.pose.bones['sword'].tail-center).normalized()
    handle=BVHTree.FromPolygons(pts,[list(f.vertices) for f in weapon.data.polygons if all(-.112<(pts[i]-center).dot(axis)<.085 for i in f.vertices)])
    max_depth=0; invalid=0; disagree=0
    samples=[ev.matrix_world@ev.data.vertices[i].co for i in indices]
    for i in face_ids:
        vs=[ev.matrix_world@ev.data.vertices[j].co for j in ev.data.polygons[i].vertices]; samples.append(sum(vs,Vector())/len(vs))
    for p in samples:
        _,_,_,dist=solid.find_nearest(p)
        if dist<.001: continue
        votes=[interior(solid,p,r) for r in directions]
        if votes[0]!=votes[1]: disagree+=1
        if all(votes): invalid+=1; max_depth=max(max_depth,dist)
    contacts={}
    for name,ids in state['contact_pad_vertices']['R'].items():
        ds=[handle.find_nearest(ev.matrix_world@ev.data.vertices[i].co)[3] for i in ids]
        contacts[name]={'within2mm':sum(d<=.002 for d in ds),'minimum_m':min(ds),'mean_m':sum(ds)/len(ds)}
    contact_loss=sum(sorted(handle.find_nearest(ev.matrix_world@ev.data.vertices[i].co)[3] for i in ids)[:3][0] for ids in state['contact_pad_vertices']['R'].values())
    safe=invalid==0 and disagree==0
    return {'parameters':[f,d,angle],'thumb_offset':list(state['thumb_offsets']['R']),'samples':len(samples),'inside_deeper_than1mm':invalid,'max_penetration_m':max_depth,'ray_disagreements':disagree,'fixed_pad_contacts':contacts,'hard_surface_constraint_met':safe,'contact_loss':contact_loss}
log=[]; candidates=[]
for f in [.031,.043,.055]:
    for d in [-.008,.010,.028]:
        for angle in [.65,.85,1.05]:
            if len(log)>=30 or start['contact_search_prior_evaluations']+len(log)>=start['contact_search_global_maximum']: raise RuntimeError('Shared search exhausted')
            row=evaluate(f,d,angle); log.append(row); candidates.append((row,copy.deepcopy(state)))
safe=[x for x in candidates if x[0]['hard_surface_constraint_met']]
# Preserve a failed specimen when every candidate violates the hard constraint; never call it accepted.
chosen=min(safe,key=lambda x:x[0]['contact_loss']) if safe else min(candidates,key=lambda x:(x[0]['inside_deeper_than1mm'],x[0]['max_penetration_m']))
row,chosen_state=chosen; state=copy.deepcopy(chosen_state)
for thumb in [[-.020,.009,-.020],[-.030,.022,-.020],[-.030,.009,-.005]]:
    f,d,a=row['parameters']; candidate=evaluate(f,d,a,thumb); log.append(candidate)
    if candidate['hard_surface_constraint_met'] and (not row['hard_surface_constraint_met'] or candidate['contact_loss']<row['contact_loss']): row=candidate; chosen_state=copy.deepcopy(state)
state=copy.deepcopy(chosen_state); final=evaluate(*row['parameters'],state['thumb_offsets']['R'])
# Final repeat is a readback, not another searched candidate.30 searches +100prior =130 total.
QA.mkdir(parents=True); OUT.mkdir(parents=True); (QA/'rig-helper-used.py').write_bytes((ROOT/'scripts/ro_core_rig.py').read_bytes())
mat=bpy.data.materials.new('Diagnostic_gray_surface'); mat.use_nodes=True; mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.28,.32,.38,1)
deps=bpy.context.evaluated_depsgraph_get(); ev=core.evaluated_get(deps)
ids={v.index for v in core.data.vertices if v.co.x<-.34 and v.co.z<.99}; faces=[list(f.vertices) for f in core.data.polygons if all(i in ids for i in f.vertices)]
mesh=bpy.data.meshes.new('Right_actual_surface'); mesh.from_pydata([ev.matrix_world@v.co for v in ev.data.vertices],[],faces); mesh.materials.append(mat)
ob=bpy.data.objects.new('Actual_right_hand_diagnostic',mesh); bpy.context.scene.collection.objects.link(ob)
for p in mesh.polygons: p.use_smooth=True
for item in bpy.data.collections['COL_Character'].objects:
    if item.type=='MESH' and item!=sword: item.hide_render=True
target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.65)
for name,offset in [('front',(.30,-1,.15)),('side',(1,0,.12)),('back',(-.3,1,.12)),('under',(0,-.25,-1))]:
    camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(QA/(name+'.png')); bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(ob,do_unlink=True); bpy.data.meshes.remove(mesh)
for item in bpy.data.collections['COL_Character'].objects: item.hide_render=False
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); rig['state_json']=json.dumps(state); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_surface_specimen.blend'))
report={'trial':'v003','source':previous['artifact'],'thumb_port_weight_vertices_changed':len(changed),'geometry_and_uv_unchanged':True,
    'search_prior':100,'new_searches':len(log),'global_search_used':100+len(log),'global_search_limit':160,'right_hand_search_limit':80,'right_hand_prior_assumed50':True,
    'prototype_clock_reset':False,'safe_candidates':sum(r['hard_surface_constraint_met'] for r in log),'selected':final,'search_log':log,
    'selection_rule':'Only zero deep sample penetration and zero ray disagreement may be considered. If none, preserve the least-violating failed specimen and stop; contact improvement cannot compensate.',
    'surface_contact_accepted':False,'art_accepted':False,'artifact':{'path':(OUT/'ro_surface_specimen.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_surface_specimen.blend').read_bytes()).hexdigest()}}
(QA/'surface.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print('RO_HAND_SURFACE_FINAL '+json.dumps({k:v for k,v in report.items() if k!='search_log'}))
