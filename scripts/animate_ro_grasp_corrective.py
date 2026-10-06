"""Bake and verify the fixed local grasp interval; no shape/control search."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,struct,bpy,numpy as np
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated
from ro_world_grasp_gate import world_contacts
from ro_pose_corrective_math import smoothstep
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
start=read(QA/'v003-start.json');result=read(QA/'v003-index-pulp/result.json');assert result['numeric_gate']
contract=read(QA/'local-contract.json');folder=QA/'v003-local-animation';folder.mkdir()
out=ROOT/'assets/processed/ro-swordsman-combo-r010/v003-local-animation';out.mkdir(parents=True)
save(folder/'start.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'candidate':'v003','source':result['artifact'],
 'new_model_search':False,'curve':'smoothstep closure frame1..31, morph=t^3, frame31..61 hold; hand rigid motion after31; baked integerframes and sampledhalfframes',
 'contact_establishment_frame':31,'scope':'local diagnostic only, not full300','controls_source':result['controls_source']})
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];weapon=bpy.data.objects['SM_RO_LocalActualSword']
assert all(max(abs(o.matrix_world[i][j]-Matrix.Identity(4)[i][j]) for i in range(4) for j in range(4))<1e-8 for o in [ob,rig,weapon])
rest=common.geometry(ob);ww=common.weights(ob);sourcepose=read(ROOT/result['controls_source']['path']);key=ob.data.shape_keys.key_blocks[result['shape_key']]
before,_,_=evaluated(weapon);assert not weapon.modifiers
for mesh,name in [(ob,'_r010_id'),(weapon,'_r010_weapon_id')]:
    attribute=mesh.data.attributes.new(name,'FLOAT','POINT')
    for i,row in enumerate(attribute.data):row.value=i
    mesh.parent=rig;mesh.matrix_parent_inverse=Matrix.Identity(4);mesh.matrix_basis=Matrix.Identity(4)
group=weapon.vertex_groups.new(name='sword');group.add(list(range(len(weapon.data.vertices))),1.,'REPLACE')
modifier=weapon.modifiers.new('RigidSwordFollow','ARMATURE');modifier.object=rig
after,_,_=evaluated(weapon);bind_error=max((a-b).length for a,b in zip(before,after));assert bind_error<1e-6
rig.animation_data_clear();ob.data.shape_keys.animation_data_clear()
scene=bpy.context.scene;scene.render.fps=60;scene.frame_start=1;scene.frame_end=61
for frame in range(1,62):
    scene.frame_set(frame)
    t=smoothstep(0,1,(frame-1)/30)
    row={n:[a*t for a in sourcepose['controls'][n]] for n in ['finger1','finger2','finger3','finger4','thumb']};row['pronation']=sourcepose['controls']['pronation']*t
    splays={n:a*t for n,a in sourcepose['splays'].items()}
    grip.controls(rig,row,splays,splay_first=True)
    u=max(0,(frame-31)/30)
    rig.pose.bones['hand'].matrix_basis=Matrix.Translation(Vector((.012*u,.018*u,.015*u)))@Matrix.Rotation(.12*u,4,'Z')
    key.value=t**3
    for bone in rig.pose.bones:
        bone.rotation_mode='QUATERNION'
        for path in ['location','rotation_quaternion','scale']:bone.keyframe_insert(data_path=path,frame=frame,group=bone.name)
    key.keyframe_insert(data_path='value',frame=frame)
rig.animation_data.action.name='AN_RO_RightHand_GraspDiagnostic';ob.data.shape_keys.animation_data.action.name='AN_RO_RightHand_GraspMorph'
for data in [rig,ob.data.shape_keys]:
    for curve in data.animation_data.action.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'

def set_frame(frame):scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
def weapon_error():
    pts,_,_=evaluated(weapon);b=rig.pose.bones['sword'];matrix=rig.matrix_world@b.matrix@rig.data.bones['sword'].matrix_local.inverted()
    return max((p-matrix@v.co).length for p,v in zip(pts,weapon.data.vertices))

set_frame(31);key_checks=[]
for value in [0.,.25,.5,.75,1.]:
    key.value=value;bpy.context.view_layer.update();pts,_,_=evaluated(ob)
    if value==0:zero=[p.copy() for p in pts]
    if value==1:one=[p.copy() for p in pts]
    report,_=grip.capture(ob,rig,rest,'key-'+str(value),[],ww)
    contact=world_contacts(ob,weapon,rig,contract['pads'],'key-'+str(value),{'value':value})
    key_checks.append({'value':value,'self':report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'depth_m':contact['maximum_penetration_m'],
        'unknown':len(contact['unknown_inside']),'minratio':report['minimum_edge_ratio'],'maxratio':report['maximum_edge_stretch'],'points':[list(p) for p in pts]})
for row in key_checks:
    target=[a.lerp(b,row['value']) for a,b in zip(zero,one)]
    row['linear_skin_key_error_m']=max((Vector(p)-t).length for p,t in zip(row.pop('points'),target));assert row['linear_skin_key_error_m']<1e-6
assert max((one[i]-zero[i]).length for i in contract['thumb_protected_ids'])<1e-7
save(folder/'key-value-verification.json',{'checks':key_checks,'protected_thumb_samepose_extra_m':max((one[i]-zero[i]).length for i in contract['thumb_protected_ids'])})

frames=[1+i*.5 for i in range(121)];events=[];hand_points=[];weapon_points=[];head_points=[];tail_points=[]
for index,frame in enumerate(frames):
    set_frame(frame)
    report,localpoints=grip.capture(ob,rig,rest,'frame-'+str(frame),[],ww)
    contact=world_contacts(ob,weapon,rig,contract['pads'],'frame-'+str(frame),{'frame':frame,'key':key.value})
    depth=contact['maximum_penetration_m'];required=frame>=31
    surface_ok=not report['transverse_pairs'] and not report['degenerate_triangles'] and not contact['transverse_crossings_count'] and not contact['unknown_inside'] and depth<=.001 and report['minimum_edge_ratio']>=.25 and report['maximum_edge_stretch']<=3
    ok=surface_ok and (not required or contact['surface_gate_pass'])
    hp,_,_=evaluated(ob);wp,_,_=evaluated(weapon);b=rig.pose.bones['sword'];err=weapon_error();assert err<1e-6
    event={'frame':frame,'contact_required':required,'key_value':key.value,'surface_ok':surface_ok,'pass':ok,'self':report['transverse_pairs'],'sword':contact['transverse_crossings_count'],
        'depth_m':depth,'unknown':len(contact['unknown_inside']),'minratio':report['minimum_edge_ratio'],'maxratio':report['maximum_edge_stretch'],
        'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'weapon_rigid_max_error_m':err}
    events.append(event);hand_points.append([list(p) for p in hp]);weapon_points.append([list(p) for p in wp]);head_points.append(list(rig.matrix_world@b.head));tail_points.append(list(rig.matrix_world@b.tail))
    with (folder/'interval-events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
    if index%20==0:print('INTERVAL_PROGRESS '+json.dumps(event),flush=True)

set_frame(31);reference=world_contacts(ob,weapon,rig,contract['pads'],'identity',{})
rig.matrix_world=Matrix.Translation(Vector((.3,-.2,.1)))@Matrix.Rotation(.37,4,'Z');bpy.context.view_layer.update()
transformed=world_contacts(ob,weapon,rig,contract['pads'],'rigid-world-transform',{})
world_error=weapon_error();assert world_error<1e-6
assert {n:r['within_2mm'] for n,r in transformed['pad_contacts'].items()}=={n:r['within_2mm'] for n,r in reference['pad_contacts'].items()}
save(folder/'weapon-world-frame-verification.json',{'bind_error_m':bind_error,'transformed_rigid_error_m':world_error,
 'contacts_identity':{n:r['within_2mm'] for n,r in reference['pad_contacts'].items()},'contacts_transformed':{n:r['within_2mm'] for n,r in transformed['pad_contacts'].items()},
 'world_space_gate':'Originalthresholds, swordhead/tail transformed byrig.matrix_world','no_scaling_or_sliding':True})
rig.matrix_world=Matrix.Identity(4);set_frame(31)
with (folder/'expected-animation-points.npz').open('xb') as f:np.savez_compressed(f,frames=np.array(frames),hand=np.array(hand_points),weapon=np.array(weapon_points),sword_head=np.array(head_points),sword_tail=np.array(tail_points))
dest=out/'right_hand_grasp_61f.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
for frame in [1,16,31,46,61]:set_frame(frame);common.render(folder,'frame-'+str(frame),['palm','side'])
set_frame(31)
all_ok=all(r['pass'] for r in events);glb=None;structure=None
if all_ok:
    bpy.ops.object.select_all(action='DESELECT')
    for item in [rig,ob,weapon]:item.select_set(True)
    bpy.context.view_layer.objects.active=rig
    glb=out/'right_hand_grasp_61f.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_skins=True,
        export_morph=True,export_morph_animation=True,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True,
        export_frame_range=True,export_frame_step=1,export_attributes=True)
    blob=glb.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length].decode('utf-8'))
    structure={'meshes':[{'name':m.get('name'),'attributes':[list(p['attributes']) for p in m['primitives']],'morph_counts':[len(p.get('targets',[])) for p in m['primitives']]} for m in doc['meshes']],
        'skins':len(doc.get('skins',[])),'animations':[{'name':a.get('name'),'target_paths':sorted(set(c['target']['path'] for c in a['channels']))} for a in doc.get('animations',[])]}
    save(folder/'glb-structure.json',structure)
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':result['artifact'],'artifact':artifact(dest),'glb':artifact(glb) if glb else None,
 'interval_samples':len(events),'integer_frames':61,'half_frames':60,'required_grasp_samples':sum(r['contact_required'] for r in events),
 'interval_numeric_pass':all_ok,'first_failure':next((r for r in events if not r['pass']),None),'failures':sum(not r['pass'] for r in events),
 'minimum_ratio':min(r['minratio'] for r in events),'maximum_ratio':max(r['maxratio'] for r in events),
 'expected_points':artifact(folder/'expected-animation-points.npz'),'frame_coordinate_checks':artifact(folder/'weapon-world-frame-verification.json'),
 'key_value_checks':artifact(folder/'key-value-verification.json'),'views':[artifact(p) for p in sorted(folder.glob('*.png'))],
 'fresh_blend_glb':'pending','full300_and_art_acceptance':False,'new_credits':0})
print('R010_INTERVAL_RESULT '+str({'numeric_pass':all_ok,'samples':len(events),'failures':sum(not r['pass'] for r in events),'first_failure':next((r for r in events if not r['pass']),None),'exported':bool(glb)}),flush=True)
