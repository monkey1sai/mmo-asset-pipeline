"""v005 two checkpoints: frozen-region thumb sculpt; measured cuff/helper transitions."""
from datetime import datetime,timezone
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign,curl_digits
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_hand_gate import contacts,evaluated,sword_solid,segment_hit
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v005-thumb-wrist'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v005-thumb-wrist'
start=json.loads((BASEQA/'v005-start.json').read_text()); clock=json.loads((BASEQA/'phase-start.json').read_text()); source=ROOT/start['source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']; assert not QA.exists() and not OUT.exists()
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; sword=bpy.data.objects['SM_RO_sword']; core=bpy.data.objects['SM_RO_core']
state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); pads=json.loads(glove['fixed_pad_indices'])
basis=glove.data.shape_keys.key_blocks['Basis']; key=glove.data.shape_keys.key_blocks['GripContact_R']; key.value=1
OUT.mkdir(parents=True); QA.mkdir(parents=True)
def save(p,value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
neighbors={i:set() for i in range(len(glove.data.vertices))}
for e in glove.data.edges:
    a,b=e.vertices; neighbors[a].add(b); neighbors[b].add(a)
region=set(pads['thumb']); ring=set().union(*(neighbors[i] for i in region))-region
weights={i:1 for i in region}; weights.update({i:.5 for i in ring})
save(QA/'fixed-thumb-sculpt-region.json',{'mask':pads['thumb'],'one_ring':sorted(ring),'vertex_falloff':weights,
    'distance_falloff':'smoothstep1-distance/4.5mm; full region fixed before sculpt','maximum_cumulative_basis_delta_m':.005})
configure(rig,state,params); events=[]
def event(label):
    guard(); r=contacts(glove,sword,rig,pads,'single-grip',{'joint_ik':params,'checkpoint':label,'corrective':key.value})
    r.update(event_kind=label,event_number=len(events)+1,timestamp_utc=datetime.now(timezone.utc).isoformat())
    events.append(r); save(QA/'contact-events.json',events); return r
initial=event('initial_readback'); deltas=[]
for iteration in [1,2,3]:
    points,triangles,edges=evaluated(glove); _,_,solid=sword_solid(sword)
    changed=[]
    for i,weight in weights.items():
        hit,normal,face,distance=solid.find_nearest(points[i])
        if not .0009<distance<.0045: continue
        x=max(0,min(1,1-distance/.0045)); amount=weight*x*x*(3-2*x)
        target=points[i].lerp(hit+normal*.0009,amount)
        blend=Matrix(((0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)))
        for g in glove.data.vertices[i].groups:
            n=glove.vertex_groups[g.group].name; blend+=(rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted())*g.weight
        restored=blend.inverted()@target; total=(restored-basis.data[i].co).length
        assert total<=start['maximum_corrective_m'],'Cumulative contact sculpt exceeds5mm'
        key.data[i].co=restored; changed.append({'id':i,'cumulative_rest_delta_m':total})
    bpy.context.view_layer.update(); deltas.append({'iteration':iteration,'vertices':changed}); result=event('thumb_sculpt_candidate')
    if result['surface_gate_pass']: break
thumb=event('thumb_checkpoint_readback'); save(QA/'thumb-sculpt-deltas.json',deltas)
key.value=0
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_thumb_contact_checkpoint.blend'))
save(QA/'thumb-checkpoint.json',{'surface_gate_pass':thumb['surface_gate_pass'],'pad_contacts':thumb['pad_contacts'],
    'maximum_penetration_m':thumb['maximum_penetration_m'],'crossings':thumb['transverse_crossings_count'],
    'cuff_accepted':False,'artifact_sha256':hashlib.sha256((OUT/'ro_thumb_contact_checkpoint.blend').read_bytes()).hexdigest()})

# Discard only the task-created bad sleeve object in this NEW in-memory derivative.
bad=bpy.data.objects.get('SM_RO_WristSleeve.R')
if bad: bpy.data.objects.remove(bad,do_unlink=True)
anatomy=json.loads((BASEQA/'v001-generated-glove/anatomy-and-masks.json').read_text())
rotation=Matrix(anatomy['rotation']); source_wrist=Vector(anatomy['source_wrist']); wrist=Vector(state['rest']['hand.R'][0])
up=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized()*-1
width=Vector(state['hand_frames']['R']['width']); u=(width-up*width.dot(up)).normalized(); v=up.cross(u).normalized()
front=Vector(state['hand_frames']['R']['front'])
if v.dot(front)<0: v=-v
plane=wrist+up*.045; section=[]
for e in core.data.edges:
    a,b=(core.data.vertices[i].co for i in e.vertices)
    if any(p.x>-.33 or not .94<p.z<1.07 for p in [a,b]): continue
    da,db=(a-plane).dot(up),(b-plane).dot(up)
    if da*db>0 or abs(da-db)<1e-9: continue
    section.append(a.lerp(b,da/(da-db)))
assert len(section)>8,'Actual forearm cross-section missing'
cu=(min((p-plane).dot(u) for p in section)+max((p-plane).dot(u) for p in section))/2
cv=(min((p-plane).dot(v) for p in section)+max((p-plane).dot(v) for p in section))/2
ru=(max((p-plane).dot(u) for p in section)-min((p-plane).dot(u) for p in section))/2
rv=(max((p-plane).dot(v) for p in section)-min((p-plane).dot(v) for p in section))/2
cuff_ids=[]; source_coords={}
for vert in glove.data.vertices:
    p=rotation.inverted()@(basis.data[vert.index].co-wrist)+source_wrist
    if p.z<.052: cuff_ids.append(vert.index); source_coords[vert.index]=p
source_radial=[]
for i,p in source_coords.items():
    center=wrist+Vector(state['hand_frames']['R']['down'])*(p.z-source_wrist.z)
    r=basis.data[i].co-center
    if p.z<.020: source_radial.append((abs(r.dot(u)),abs(r.dot(v))))
su=max(a for a,b in source_radial); sv=max(b for a,b in source_radial)
cuff_changes=[]
for i,p in source_coords.items():
    original=basis.data[i].co.copy(); center=wrist+Vector(state['hand_frames']['R']['down'])*(p.z-source_wrist.z); r=original-center
    target_center=wrist-up*(p.z-source_wrist.z)+u*cu+v*cv
    target=target_center+u*(r.dot(u)/su*ru)+v*(r.dot(v)/sv*rv)
    x=max(0,min(1,(.052-p.z)/.045)); factor=x*x*(3-2*x)
    refined=original.lerp(target,factor); offset=refined-original
    for block in glove.data.shape_keys.key_blocks: block.data[i].co+=offset
    glove.data.vertices[i].co=refined; cuff_changes.append({'id':i,'source_fitting_delta_m':offset.length})
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT'); bone=rig.data.edit_bones.new('wrist_transition.R'); bone.head=wrist; bone.tail=wrist+Vector(state['hand_frames']['R']['down'])*.04
bone.parent=rig.data.edit_bones['lower_arm.R']; bpy.ops.object.mode_set(mode='OBJECT')
state['rest']['wrist_transition.R']=[list(wrist),list(wrist+Vector(state['hand_frames']['R']['down'])*.04)]
state['parents']['wrist_transition.R']='lower_arm.R'
for i,p in source_coords.items():
    if p.z<.026:
        blend=max(0,min(1,p.z/.026)); assign(glove,glove.data.vertices[i],{'lower_arm.R':1-blend,'wrist_transition.R':blend})
    else:
        blend=max(0,min(1,(p.z-.026)/.026)); assign(glove,glove.data.vertices[i],{'wrist_transition.R':1-blend,'hand.R':blend})
rig['state_json']=json.dumps(state); rig['wrist_helper_method']='slerp lower_arm and hand pose*rest^-1 rotations, wrist pivot; configure updates every time'
save(QA/'wrist-fitting.json',{'measured_forearm_section_points':len(section),'radii_m':[ru,rv],'section_center_offsets_m':[cu,cv],
    'source_cuff_radii_m':[su,sv],'changes':cuff_changes,'helper':'wrist_transition.R',
    'helper_parent':'lower_arm.R','rest':state['rest']['wrist_transition.R'],'bad_sleeve_removed_from_new_version':True,
    'new_sleeve_added':False,'reason':'First fit actual source cuff, no extra sleeve until actual gap evidence'})
key.value=1; configure(rig,state,params); final_contact=event('wrist_checkpoint_readback')
pose_basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}

def render(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
def armor_crossings():
    gp,gt,_=evaluated(glove); cuff_tri=[t for t in gt if any(i in cuff_ids for i in t)]
    a=BVHTree.FromPolygons(gp,cuff_tri,all_triangles=True); results={}
    for n in ['SM_RO_bracer.R','SM_RO_cuirass']:
        ob=bpy.data.objects.get(n)
        if ob is None: raise RuntimeError('Required armor absent: '+n)
        ap,at,_=evaluated(ob); b=BVHTree.FromPolygons(ap,at,all_triangles=True); hits=[]
        for i,j in a.overlap(b):
            x=[gp[k] for k in cuff_tri[i]]; y=[ap[k] for k in at[j]]
            if any(segment_hit(left[k],left[(k+1)%3],right) is not None for left,right in [(x,y),(y,x)] for k in range(3)):
                hits.append([i,j])
        results[n]={'transverse_triangle_pairs':len(hits),'pairs':hits}
    return results
transition=[]
for alpha in [0,.25,.5,.75,1]:
    for pb in rig.pose.bones:
        m=pose_basis[pb.name]; rotation_q=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha)
        basis_m=rotation_q.to_matrix().to_4x4(); basis_m.translation=m.translation*alpha; pb.matrix_basis=basis_m
    bpy.context.view_layer.update(); update_wrist_helper(rig); key.value=alpha; bpy.context.view_layer.update()
    collisions=armor_crossings(); transition.append({'alpha':alpha,'corrective':alpha,'armor_crossings':collisions})
    render(QA/f'transition-{alpha:g}')
save(QA/'wrist-transition.json',transition)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
key.value=0; bpy.context.view_layer.update(); render_views(QA/'whole-open')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_thumb_wrist.blend'))
whole=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.data.calc_loop_triangles(); whole+=len(ob.data.loop_triangles)
report={'trial':'v005','finished_utc':datetime.now(timezone.utc).isoformat(),'thumb_surface_gate_pass':thumb['surface_gate_pass'],
    'final_surface_gate_pass':final_contact['surface_gate_pass'],'pad_contacts':final_contact['pad_contacts'],
    'maximum_penetration_m':final_contact['maximum_penetration_m'],'sword_crossings':final_contact['transverse_crossings_count'],
    'cumulative_contact_shape_delta_m':max((a.co-b.co).length for a,b in zip(key.data,basis.data)),
    'max_cuff_source_fitting_delta_m':max(c['source_fitting_delta_m'] for c in cuff_changes),
    'transition_samples':5,'cuff_armor_transverse_pairs_by_sample':[{n:r['transverse_triangle_pairs'] for n,r in row['armor_crossings'].items()} for row in transition],
    'whole_triangles':whole,'whole_budget_pass':whole<=60000,'full_local_art_acceptance':'pending actual five transition views',
    'full_animation_accepted':False,'delivered':False,'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
    'artifact':{'path':(OUT/'ro_thumb_wrist.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_thumb_wrist.blend').read_bytes()).hexdigest()}}
save(QA/'thumb-wrist.json',report); print('RO_THUMB_WRIST '+json.dumps(report))
