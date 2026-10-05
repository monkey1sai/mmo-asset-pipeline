"""v003: independent phalanx IK against fixed actual handle, <=40 surface candidates."""
from datetime import datetime,timezone
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import pose,solve,aligned
from ro_hand_gate import contacts,evaluated,sword_solid
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v003-joint-ik'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v003-joint-ik'
start=json.loads((BASEQA/'v003-start.json').read_text()); clock=json.loads((BASEQA/'phase-start.json').read_text())
source=ROOT/start['source']['path']; assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not QA.exists() and not OUT.exists()
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; sword=bpy.data.objects['SM_RO_sword']
state=json.loads(rig['state_json']); initial=copy.deepcopy(state); pads=json.loads(glove['fixed_pad_indices'])
frame=state['hand_frames']['R']; front=Vector(frame['front']); down=Vector(frame['down']); width=Vector(frame['width'])
palm=sum((Vector(p) for p in state['measurements']['R']['knuckles']),Vector())/4
origin=palm+front*.038+down*.020
old_grip=Vector(state['grips']['R'])
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
for v in sword.data.vertices: v.co+=origin-old_grip
sword.data.update(); state['grips']['R']=list(origin)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT'); b=rig.data.edit_bones['sword']; b.head=origin; b.tail=origin-width*.8
bpy.ops.object.mode_set(mode='OBJECT'); state['rest']['sword']=[list(origin),list(origin-width*.8)]
state.pop('finger_angles',None)
QA.mkdir(parents=True); OUT.mkdir(parents=True)
def save(p,value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
invalid_results=[]
for name,corrupt in [('empty',{}),('missing_thumb',{k:v for k,v in pads.items() if k!='thumb'}),
    ('duplicates',{**pads,'thumb':[0,0,1]}),('out_of_range',{**pads,'thumb':[0,1,len(glove.data.vertices)]}),
    ('too_short',{**pads,'thumb':[0,1]})]:
    try: contacts(glove,sword,rig,corrupt,'invalid mask test',{})
    except ValueError as e: invalid_results.append({'case':name,'rejected':True,'error':str(e)})
    else: raise RuntimeError('Invalid mask falsely accepted: '+name)
save(QA/'mask-guard-tests.json',invalid_results)

def put_worlds(worlds):
    for n,matrix in worlds.items():
        if n=='hand.R': continue
        parent=state['parents'][n]; rest=rig.data.bones[n].matrix_local
        parent_world=worlds[parent] if parent in worlds else rig.pose.bones[parent].matrix
        rig.pose.bones[n].matrix_basis=rest.inverted()@rig.data.bones[parent].matrix_local@parent_world.inverted()@matrix
    bpy.context.view_layer.update()
def roll_to_normal(matrix,n,native_normal,target_normal):
    axis=matrix.to_3x3().col[1].normalized()
    old=(matrix@rig.data.bones[n].matrix_local.inverted()).to_3x3()@native_normal
    old-=axis*old.dot(axis); new=target_normal-axis*target_normal.dot(axis)
    if old.length<1e-6 or new.length<1e-6: return matrix
    old.normalize(); new.normalize(); angle=math.atan2(axis.dot(old.cross(new)),old.dot(new))
    out=(Matrix.Rotation(angle,3,axis)@matrix.to_3x3()).to_4x4(); out.translation=matrix.translation
    return out
def configure(params):
    fixture=pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),curl=.85,two_hands=False)
    hand=rig.pose.bones['hand.R']; delta=hand.matrix@rig.data.bones['hand.R'].matrix_local.inverted()
    f=(delta.to_3x3()@front).normalized(); d=(delta.to_3x3()@down).normalized(); w=(delta.to_3x3()@width).normalized()
    center=rig.pose.bones['sword'].head.copy(); worlds={'hand.R':hand.matrix.copy()}; residuals={}
    for i in range(1,5):
        names=[f'finger{i}.R_{j:02}' for j in [1,2,3]]
        h=delta@Vector(state['rest'][names[0]][0])
        lengths=[(Vector(state['rest'][n][1])-Vector(state['rest'][n][0])).length for n in names]
        c=center+w*(h-center).dot(w)
        r=params['radius']; phi=math.radians(params['phis'][i-1])
        p2=c+f*(r*math.cos(phi))+d*(r*math.sin(phi))
        p1,reached,residual=solve(h,p2,lengths[0],lengths[1],-f)
        arc=2*math.asin(min(.99,lengths[2]/(2*r)))
        desired3=c+f*(r*math.cos(phi-arc))+d*(r*math.sin(phi-arc))
        p3=reached+(desired3-reached).normalized()*lengths[2]
        residuals[f'finger{i}']={'p2_target_residual_m':residual,'centerline_radius_m':r,'arc_degrees':math.degrees(arc)}
        for n,a,b in zip(names,[h,p1,reached],[p1,reached,p3]):
            worlds[n]=aligned(delta@rig.data.bones[n].matrix_local,a,b)
    put_worlds(worlds)
    thumb_names=['thumb.R_01','thumb.R_02']; h=delta@Vector(state['rest'][thumb_names[0]][0])
    a,b=[(Vector(state['rest'][n][1])-Vector(state['rest'][n][0])).length for n in thumb_names]
    target=center+w*params['thumb_width']+f*params['thumb_front']+d*params['thumb_down']
    mid,tip,residual=solve(h,target,a,b,-d)
    thumb_worlds={'hand.R':hand.matrix.copy()}
    for n,a,b in zip(thumb_names,[h,mid],[mid,tip]):
        matrix=aligned(delta@rig.data.bones[n].matrix_local,a,b)
        if n.endswith('02'):
            matrix=roll_to_normal(matrix,n,front,center-(a+b)/2)
        thumb_worlds[n]=matrix
    put_worlds(thumb_worlds)
    fixture['independent_joint_targets']=residuals; fixture['thumb_target_residual_m']=residual
    return fixture
events=[]
def rank(result):
    # Gate-compliant solutions always rank above every failure; no scores grant PASS.
    return (not result['surface_gate_pass'],len(result['unknown_inside']),
        result['transverse_crossings_count']>0 or result['maximum_penetration_m']>.001,
        sum(max(0,3-r['within_2mm']) for r in result['pad_contacts'].values()),
        result['maximum_penetration_m']*200+result['transverse_crossings_count']*.02+
        sum(r['minimum_gap_m'] for r in result['pad_contacts'].values())*100)
def evaluate(params,kind='search_candidate'):
    guard(); assert sum(e['event_kind']=='search_candidate' for e in events)<start['maximum_search_events']
    fixture=configure(params); result=contacts(glove,sword,rig,pads,'single-grip',params)
    result.update(event_number=len(events)+1,event_kind=kind,timestamp_utc=datetime.now(timezone.utc).isoformat(),fixture=fixture)
    result['rank']=list(rank(result)); events.append(result); save(QA/'search-events.json',events)
    return result
best_params={'radius':.023,'phis':[120]*4,'thumb_width':-.02,'thumb_front':-.021,'thumb_down':0}
best=evaluate(best_params,'initial_readback')
for radius in [.020,.023,.026]:
    for phi in [100,120,140,160]:
        p=copy.deepcopy(best_params); p['radius']=radius; p['phis']=[phi]*4
        r=evaluate(p)
        if rank(r)<rank(best): best,best_params=r,p
for digit in range(4):
    seed=copy.deepcopy(best_params)
    for phi in [100,120,140,160]:
        p=copy.deepcopy(seed); p['phis'][digit]=phi; r=evaluate(p)
        if rank(r)<rank(best): best,best_params=r,p
seed=copy.deepcopy(best_params)
for f in [-.021,0,.021]:
    for d in [-.01,0,.01]:
        p=copy.deepcopy(seed); p['thumb_front']=f; p['thumb_down']=d; r=evaluate(p)
        if rank(r)<rank(best): best,best_params=r,p
final=evaluate(best_params,'final_readback')
assert len(events)==39
def views(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
views(QA/'grip-R')
hidden=[]
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH' and ob not in [glove,sword]: hidden.append((ob,ob.hide_render)); ob.hide_render=True
views(QA/'diagnostic-isolated-grip')
for ob,v in hidden: ob.hide_render=v
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); render_views(QA/'whole-open')
rig['state_json']=json.dumps(state); rig['r006_independent_grip_ik_parameters']=json.dumps(best_params)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_glove_joint_ik.blend'))
report={'trial':'v003','finished_utc':datetime.now(timezone.utc).isoformat(),
    'search_candidate_count':37,'readback_count':2,'total_events':39,'all_events_logged':True,
    'mask_guard_negative_cases':len(invalid_results),'fixed_grip_front_down_m':[.038,.020],
    'best_parameters':best_params,'surface_gate_pass':final['surface_gate_pass'],
    'maximum_penetration_m':final['maximum_penetration_m'],'crossings':final['transverse_crossings_count'],
    'pad_contacts':final['pad_contacts'],'full_animation_accepted':False,'delivered':False,
    'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
    'artifact':{'path':(OUT/'ro_glove_joint_ik.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_glove_joint_ik.blend').read_bytes()).hexdigest()}}
save(QA/'joint-ik.json',report); print('RO_GLOVE_JOINT_IK '+json.dumps(report))
