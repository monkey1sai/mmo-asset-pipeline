"""v002 evidence-driven cuff cleanup and <=40 fully logged surface searches."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign, pose, curl_digits
from ro_hand_gate import contacts
from ro_review_common import camera, render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'
QA=BASEQA/'v002-calibration'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v002-calibration'
start=json.loads((BASEQA/'v002-start.json').read_text())
source=ROOT/start['source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not QA.exists() and not OUT.exists()
clock=json.loads((BASEQA/'phase-start.json').read_text())
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; glove=bpy.data.objects['SM_RO_glove.R']; sword=bpy.data.objects['SM_RO_sword']
state=json.loads(rig['state_json']); initial=copy.deepcopy(state)
pads=json.loads(glove['fixed_pad_indices'])
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bm=bmesh.new(); bm.from_mesh(core.data)
geom=[v for v in bm.verts if v.co.x<-.34 and v.co.z<1.04]
geom += [e for e in bm.edges if all(v.co.x<-.34 and v.co.z<1.04 for v in e.verts)]
geom += [f for f in bm.faces if all(v.co.x<-.34 and v.co.z<1.04 for v in f.verts)]
bmesh.ops.bisect_plane(bm,geom=geom,dist=1e-7,plane_co=Vector((0,0,.970)),plane_no=Vector((0,0,1)),clear_inner=True,clear_outer=False)
discard=[v for v in bm.verts if v.co.x<-.34 and v.co.z<.970-1e-6]
bmesh.ops.delete(bm,geom=discard,context='VERTS')
bm.to_mesh(core.data); bm.free(); core.data.update()
changed=[]
for v in core.data.vertices:
    if v.co.x<-.34 and v.co.z<1.015:
        assign(core,v,{'lower_arm.R':1.0}); changed.append(v.index)
# Smooth thumb origin by its actual source centerline, including thenar falloff.
anatomy=json.loads((BASEQA/'v001-generated-glove/anatomy-and-masks.json').read_text())
rotation=Matrix(anatomy['rotation']); wrist=Vector(state['rest']['hand.R'][0]); source_wrist=Vector(anatomy['source_wrist'])
thumb_h,thumb_t=map(Vector,anatomy['source_digits']['thumb']); axis=thumb_t-thumb_h
thumb_blend=[]
for v in glove.data.vertices:
    p=rotation.inverted()@(v.co-wrist)+source_wrist
    s=(p-thumb_h).dot(axis)/axis.length_squared
    radial=(p-thumb_h-axis*s).length
    if p.x>.004 and .03<p.z<.142 and radial<.029:
        root=max(0,min(1,(s+.20)/.40))
        amount=root*max(0,min(1,(.029-radial)/.013))
        distal=max(0,min(1,(s-.43)/.18))
        assign(glove,v,{'hand.R':1-amount,'thumb.R_01':amount*(1-distal),'thumb.R_02':amount*distal})
        thumb_blend.append(v.index)
OUT.mkdir(parents=True); QA.mkdir(parents=True)
def save(p,value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
frame=state['hand_frames']['R']; front=Vector(frame['front']); down=Vector(frame['down']); width=Vector(frame['width'])
palm=sum((Vector(p) for p in state['measurements']['R']['knuckles']),Vector())/4
original_grip=Vector(initial['grips']['R']); original_sword=[v.co.copy() for v in sword.data.vertices]
events=[]
def configure(params):
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    origin=palm+front*params['front']+down*params['down']
    state['grips']['R']=list(origin)
    for v,p in zip(sword.data.vertices,original_sword): v.co=p+origin-original_grip
    sword.data.update()
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT'); b=rig.data.edit_bones['sword']; b.head=origin; b.tail=origin-width*.8
    bpy.ops.object.mode_set(mode='OBJECT')
    state['rest']['sword']=[list(origin),list(origin-width*.8)]
    state['finger_angles']={'R':{str(i):[a,a*1.4,a*.85] for i,a in enumerate(params['angles'],1)}}
    state.setdefault('thumb_offsets',{})['R']=params['thumb']
    return pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),curl=.85,two_hands=False)
def objective(result):
    gap=sum(max(0,r['mean_gap_m']-.008)*300 for r in result['pad_contacts'].values())
    gap+=sum(max(0,3-r['within_2mm'])*3 for r in result['pad_contacts'].values())
    return len(result['unknown_inside'])*10000+result['maximum_penetration_m']*10000+result['transverse_crossings_count']*.35+gap
def evaluate(params,kind='search_candidate'):
    guard()
    assert len([e for e in events if e['event_kind']=='search_candidate'])<start['maximum_search_events']
    fixture=configure(params)
    result=contacts(glove,sword,rig,pads,'single-grip',params)
    result.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),event_kind=kind,event_number=len(events)+1,fixture=fixture)
    result['objective']=objective(result)
    events.append(result); save(QA/'search-events.json',events)
    return result
best_params={'front':.030,'down':.020,'angles':[.85]*4,'thumb':[-.02,.018,-.004]}
best=evaluate(best_params,'initial_readback')
for f in [.038,.046,.054]:
    for d in [.008,.020,.032]:
        p=copy.deepcopy(best_params); p['front']=f; p['down']=d
        r=evaluate(p)
        if r['objective']<best['objective']: best,best_params=r,p
for digit in range(4):
    seed=copy.deepcopy(best_params)
    for a in [.55,.75,.95,1.15]:
        p=copy.deepcopy(seed); p['angles'][digit]=a
        r=evaluate(p)
        if r['objective']<best['objective']: best,best_params=r,p
seed=copy.deepcopy(best_params)
for front_offset in [-.028,-.020,-.012]:
    for down_offset in [-.012,0,.012]:
        p=copy.deepcopy(seed); p['thumb']=[-.020,front_offset,down_offset]
        r=evaluate(p)
        if r['objective']<best['objective']: best,best_params=r,p
final=evaluate(best_params,'final_readback')
assert len(events)==36
rig['state_json']=json.dumps(state)
def hand_views(folder):
    folder.mkdir(parents=True,exist_ok=False)
    target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png'))
        bpy.ops.render.render(write_still=True)
hand_views(QA/'grip-R')
# Additional unoccluded diagnostics never replace assembled required views.
hidden=[]
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH' and ob not in [glove,sword]: hidden.append((ob,ob.hide_render)); ob.hide_render=True
hand_views(QA/'diagnostic-isolated-grip')
for ob,value in hidden: ob.hide_render=value
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); render_views(QA/'whole-open'); hand_views(QA/'open-R')
grip_angles=state.pop('finger_angles')
curl_digits(rig,state,'R',.30); hand_views(QA/'small-curl-R')
state['finger_angles']=grip_angles
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); rig['state_json']=json.dumps(state)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_glove_calibration.blend'))
triangles=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.data.calc_loop_triangles(); triangles+=len(ob.data.loop_triangles)
report={'trial':'v002','finished_utc':datetime.now(timezone.utc).isoformat(),
    'changed_old_cuff_weights':len(changed),'cuff_cut_world_z_m':.970,'thumb_blended_vertices':len(thumb_blend),
    'search_candidate_count':34,'readback_count':2,'total_events':len(events),'maximum_search_candidates':40,
    'all_events_logged':True,'best_parameters':best_params,'whole_triangles':triangles,
    'surface_gate_pass':final['surface_gate_pass'],'maximum_penetration_m':final['maximum_penetration_m'],
    'crossings':final['transverse_crossings_count'],'pad_contacts':final['pad_contacts'],
    'art_acceptance':'pending','full_animation_accepted':False,'delivered':False,
    'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
    'artifact':{'path':(OUT/'ro_glove_calibration.blend').relative_to(ROOT).as_posix(),
                'sha256':hashlib.sha256((OUT/'ro_glove_calibration.blend').read_bytes()).hexdigest()}}
save(QA/'calibration.json',report)
print('RO_GLOVE_CALIBRATION '+json.dumps(report))
