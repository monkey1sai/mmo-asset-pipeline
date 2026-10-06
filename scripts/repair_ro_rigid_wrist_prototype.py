"""v008 measured rigid binding repair; protected-ring corrective61frame prototype."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_core_rig import assign
from ro_hand_gate import contacts,evaluated,segment_hit
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v008-rigid-wrist'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v008-rigid-wrist'
start=json.loads((BASEQA/'v008-start.json').read_text()); clock=json.loads((BASEQA/'phase-start.json').read_text()); source=ROOT/start['source']['path']
assert not QA.exists() and not OUT.exists(); assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
def save(name,value): (QA/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False); QA.mkdir(parents=True); OUT.mkdir(parents=True)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; glove=bpy.data.objects['SM_RO_glove.R']; tube=bpy.data.objects['SM_RO_WristLoft.R']; bracer=bpy.data.objects['SM_RO_bracer.R']; sword=bpy.data.objects['SM_RO_sword']
state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); pads=json.loads(glove['fixed_pad_indices']); key=glove.data.shape_keys.key_blocks['GripContact_R']
rest_bracer=[v.co.copy() for v in bracer.data.vertices]
for vert in bracer.data.vertices: assign(bracer,vert,{'lower_arm.R':1})
assert all((v.co-p).length<1e-8 for v,p in zip(bracer.data.vertices,rest_bracer))
save('rigid-binding-repair.json',{'observed_original_unweighted':265,'actual_vertices_rebound':len(rest_bracer),'verified_source_rigid_bone':'lower_arm.R',
 'weight':1,'rest_geometry_unchanged':True,'evidence':'boolean-binding-diagnosis.json + wrist-volume-diagnosis.json','method':'bind all rigid vertices explicitly after topology operation; never assume Boolean propagates weights'})

ring=json.loads((BASEQA/'v006-wrist-loft-attempt2/ring-loft.json').read_text()); ci=ring['core_boundary_indices']; gi=ring['glove_boundary_indices']; ii=ring['inner_glove_boundary_indices']; sizes=[len(ci),48,48,48,len(gi),len(ci),48,48,48,len(ii)]; ranges=[]; acc=0
for size in sizes: ranges.append(list(range(acc,acc+size))); acc+=size
assert acc==len(tube.data.vertices); rest=[v.co.copy() for v in tube.data.vertices]
protected=set(ranges[0]+ranges[4]+ranges[5]+ranges[9]); middle=set(range(acc))-protected
basis=tube.shape_key_add(name='Basis'); corrections={a:tube.shape_key_add(name=f'WristVolume_{round(a*100):03d}') for a in [.25,.5,.75,1]}
key.value=1; configure(rig,state,params); final_basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}
def setpose(alpha):
    for pb in rig.pose.bones:
        m=final_basis[pb.name]; b=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha).to_matrix().to_4x4(); b.translation=m.translation*alpha; pb.matrix_basis=b
    bpy.context.view_layer.update(); update_wrist_helper(rig); key.value=alpha
    for block in corrections.values(): block.value=0
    bpy.context.view_layer.update()
def resample(points,n):
    lengths=[(b-a).length for a,b in zip(points,points[1:]+points[:1])]; total=sum(lengths); fractions=[0]
    for length in lengths: fractions.append(fractions[-1]+length/total)
    result=[]
    for i in range(n):
        t=i/n; j=next(j for j in range(len(points)) if fractions[j]<=t<=fractions[j+1]); result.append(points[j].lerp(points[(j+1)%len(points)],(t-fractions[j])/(fractions[j+1]-fractions[j])))
    return result
def rotation_fit(before,after):
    a=np.array([list(p) for p in before]); b=np.array([list(p) for p in after]); a-=a.mean(axis=0); b-=b.mean(axis=0); U,S,V=np.linalg.svd(a.T@b); r=V.T@U.T
    if np.linalg.det(r)<0: V[2]*=-1; r=V.T@U.T
    return Matrix(r.tolist()).to_quaternion()
sculpt=[]
for alpha,block in corrections.items():
    setpose(alpha); posed,_,_=evaluated(tube); deltas=[]
    for offset in [0,5]:
        A=[posed[i] for i in ranges[offset]]; B=[posed[i] for i in ranges[offset+4]]; a=[rest[i] for i in ranges[offset]]; b=[rest[i] for i in ranges[offset+4]]
        ca=sum(a,Vector())/len(a); cb=sum(b,Vector())/len(b); CA=sum(A,Vector())/len(A); CB=sum(B,Vector())/len(B); qa=rotation_fit(a,A); qb=rotation_fit(b,B); ar=resample(a,48); br=resample(b,48)
        for row,t in [(1,.25),(2,.5),(3,.75)]:
            center=CA.lerp(CB,t); rotation=qa.slerp(qb,t).to_matrix()
            for i,p,q in zip(ranges[offset+row],ar,br):
                target=center+rotation@((p-ca).lerp(q-cb,t)); blend=Matrix(((0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)))
                for g in tube.data.vertices[i].groups:
                    n=tube.vertex_groups[g.group].name; blend+=(rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted())*g.weight
                assert abs(blend.determinant())>1e-6,'Singular LBS inverse invalidates correction'
                block.data[i].co=blend.inverted()@target; deltas.append({'id':i,'rest_correction_m':(block.data[i].co-rest[i]).length,'posed_target_shift_m':(target-posed[i]).length})
    assert all((block.data[i].co-rest[i]).length<1e-8 for i in protected)
    sculpt.append({'alpha':alpha,'changed_middle_vertices':len(deltas),'max_rest_correction_m':max(d['rest_correction_m'] for d in deltas),'deltas':deltas})
save('middle-ring-correction.json',{'method':'pose-derived ring-centerline and quaternion section orientation; invert actual LBS only at middle rows, protected endpoint positions unchanged',
 'scope':'bounded local prototype4corrective states; no automatic general full-combat correction','protected_endpoint_vertices':len(protected),'protected_max_delta_m':0,'states':sculpt})
def applycorrection(alpha):
    for a,block in corrections.items(): block.value=max(0,1-abs(alpha-a)/.25)
    bpy.context.view_layer.update()
def intersections(aob,bob):
    ap,at,_=evaluated(aob); bp,bt,_=evaluated(bob); a=BVHTree.FromPolygons(ap,at,all_triangles=True); b=BVHTree.FromPolygons(bp,bt,all_triangles=True); hits=[]
    for i,j in a.overlap(b):
        left=[ap[k] for k in at[i]]; right=[bp[k] for k in bt[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(left,right),(right,left)] for k in range(3)): hits.append([i,j])
    return {'transverse_pairs':len(hits),'pairs':hits}
def selfcross(ob):
    points,triangles,_=evaluated(ob); bm=bmesh.new(); bm.from_mesh(ob.data)
    for vert,p in zip(bm.verts,points): vert.co=p
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6); bmesh.ops.triangulate(bm,faces=list(bm.faces)); bm.verts.ensure_lookup_table(); bm.verts.index_update(); bm.faces.ensure_lookup_table()
    ps=[v.co.copy() for v in bm.verts]; ts=[[v.index for v in f.verts] for f in bm.faces]; tree=BVHTree.FromPolygons(ps,ts,all_triangles=True); hits=[]
    for i,j in tree.overlap(tree):
        if i>=j or set(ts[i])&set(ts[j]): continue
        left=[ps[k] for k in ts[i]]; right=[ps[k] for k in ts[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(left,right),(right,left)] for k in range(3)): hits.append([i,j])
    bm.free(); return {'nonadjacent_transverse_pairs':len(hits),'pairs':hits,'method':'evaluated positions diagnostic weld1um, skip shared-vertex neighboring faces, actual segment/triangle crossings; tangential contacts excluded'}
def rigid_error(ob,bone):
    points,_,_=evaluated(ob); delta=rig.pose.bones[bone].matrix@rig.data.bones[bone].matrix_local.inverted()
    return max((p-delta@v.co).length for p,v in zip(points,ob.data.vertices))
def render(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
samples=[]
for alpha in [0,.25,.5,.75,1]:
    guard(); setpose(alpha); applycorrection(alpha); tp,_,_=evaluated(tube); gp,_,_=evaluated(glove); cp,_,_=evaluated(core)
    seams=max(max((tp[ranges[0][i]]-cp[ci[i]]).length for i in range(len(ci))),max((tp[ranges[4][i]]-gp[gi[i]]).length for i in range(len(gi))),max((tp[ranges[9][i]]-gp[ii[i]]).length for i in range(len(ii))))
    sample={'alpha':alpha,'seams_max_m':seams,'rigid_prediction_max_errors_m':{ob.name:rigid_error(ob,bone) for ob,bone in [(bracer,'lower_arm.R'),(bpy.data.objects['SM_RO_pauldron.R'],'pauldron.R'),(bpy.data.objects['SM_RO_pauldron.L'],'pauldron.L')]},
     'armor_collisions':{ob.name:intersections(ob,bracer) for ob in [glove,tube,core]},'glove_self_crossings':selfcross(glove),'tube_self_crossings':selfcross(tube)}
    samples.append(sample); render(QA/f'transition-{alpha:g}')
save('wrist-transition.json',samples)
setpose(1); applycorrection(1); contact=contacts(glove,sword,rig,pads,'single-grip',{'joint_ik':params,'checkpoint':'rigid_binding_and_ring_volume'})
contact.update(event_kind='final_readback',event_number=1,timestamp_utc=datetime.now(timezone.utc).isoformat()); save('contact-events.json',[contact])

# Every frame stores actual helper matrices and corrective values; prototype is1second only.
scene=bpy.context.scene; scene.render.fps=60; scene.frame_start=1; scene.frame_end=61; scene['animation_scope']='Local wrist open-to-grip prototype; NOT300frameROcombo'
for frame in range(1,62):
    alpha=(frame-1)/60; scene.frame_set(frame); setpose(alpha); applycorrection(alpha)
    for pb in rig.pose.bones:
        pb.rotation_mode='QUATERNION'; pb.keyframe_insert(data_path='location',frame=frame); pb.keyframe_insert(data_path='rotation_quaternion',frame=frame); pb.keyframe_insert(data_path='scale',frame=frame)
    key.keyframe_insert(data_path='value',frame=frame)
    for block in corrections.values(): block.keyframe_insert(data_path='value',frame=frame)
for data in [rig,glove.data.shape_keys,tube.data.shape_keys]:
    if data.animation_data and data.animation_data.action: data.animation_data.action.name=('RO_WristGrip_Prototype_61f_'+data.name)[:63]
scene.frame_set(1); bpy.context.view_layer.update(); render_views(QA/'whole-open')
checkpoints=[]
for frame in [1,16,31,46,61]:
    scene.frame_set(frame); bpy.context.view_layer.update(); objects={}
    for ob in [glove,tube,bracer,core,sword]:
        points,triangles,_=evaluated(ob); objects[ob.name]={'positions':[list(p) for p in points],'triangles':triangles}
    checkpoints.append({'frame':frame,'objects':objects})
save('roundtrip-expected.json',{'fps':60,'frames':[1,61],'purpose':'Actual local wrist/sword skeletal plus morph playback; not full skill sequence orVFX','checkpoints':checkpoints})
scene.frame_set(1); bpy.context.view_layer.update(); p=OUT/'ro_wrist_grip_prototype.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(p))
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
whole=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.select_set(True); ob.data.calc_loop_triangles(); whole+=len(ob.data.loop_triangles)
bpy.context.view_layer.objects.active=rig
glb=OUT/'ro_wrist_grip_prototype.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_force_sampling=True,export_frame_range=True,export_skins=True,export_morph=True,export_morph_animation=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_current_frame=False)
report={'trial':'v008','finished_utc':datetime.now(timezone.utc).isoformat(),'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
 'surface_gate_pass':contact['surface_gate_pass'],'pad_contacts':contact['pad_contacts'],'maximum_penetration_m':contact['maximum_penetration_m'],'sword_crossings':contact['transverse_crossings_count'],
 'whole_triangles':whole,'whole_budget_pass':whole<=60000,'seams_max_m':max(s['seams_max_m'] for s in samples),'rigid_prediction_max_error_m':max(v for s in samples for v in s['rigid_prediction_max_errors_m'].values()),
 'armor_crossings_by_sample':[{n:r['transverse_pairs'] for n,r in s['armor_collisions'].items()} for s in samples],
 'glove_self_crossings_by_sample':[s['glove_self_crossings']['nonadjacent_transverse_pairs'] for s in samples],'tube_self_crossings_by_sample':[s['tube_self_crossings']['nonadjacent_transverse_pairs'] for s in samples],
 'maximum_new_wrist_corrective_m':max(s['max_rest_correction_m'] for s in sculpt),'prototype_animation':{'frames':61,'fps':60,'seconds':1,'full_skill_combo':False},
 'art_acceptance':'pending actual fixed views','fresh_glb_roundtrip':'not_run_yet','full_animation_accepted':False,'left_replacement_accepted':False,'delivered':False,
 'artifacts':[{'path':v.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for v in [p,glb]]}
save('rigid-wrist.json',report); print('RO_RIGID_WRIST '+json.dumps(report))
