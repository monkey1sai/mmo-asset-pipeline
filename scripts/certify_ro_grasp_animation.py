"""Verify unchanged saved animation under supplemental certified classification."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,struct,shutil,bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated,sword_solid,inside
from ro_certified_grasp_gate import certified_contacts
from ro_solid_angle import certify_oriented_closed,classify_winding
from mathutils import Vector
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
start=read(QA/'v004-start.json');contract=read(QA/'local-contract.json');folder=QA/'v004-certified-animation';folder.mkdir()
out=ROOT/'assets/processed/ro-swordsman-combo-r010/v004-certified-animation';out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
expected=np.load(ROOT/start['expected_points']['path'])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];weapon=bpy.data.objects['SM_RO_LocalActualSword']
scene=bpy.context.scene;rest=common.geometry(ob);ww=common.weights(ob);rows=[];max_hand=0.;max_weapon=0.;heads=[];tails=[]
scene.frame_set(46,subframe=.5);bpy.context.view_layer.update()
sp,st,tree=sword_solid(weapon);certification=certify_oriented_closed(sp,st)
diagnostic=read(QA/'v003-local-animation/ray-ambiguity-diagnosis.json')['unknown_sample_diagnosis'][0]
point=np.array(diagnostic['point'],dtype=np.float64);source=np.array(sp,dtype=np.float64)
angle=.37;c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
transformation_checks=[]
for name,matrix,translation in [('identity',np.eye(3),np.zeros(3)),('rigid',rotation,np.array([.3,-.2,.1])),('mirror',np.diag([-1,1,1]),np.zeros(3))]:
    points=source@matrix.T+translation;target=matrix@point+translation
    surface=certify_oriented_closed(points,st);vote,winding=classify_winding(points,st,target,diagnostic['nearest_m'])
    transformation_checks.append({'name':name,'inside':vote,'winding':winding,'surface':surface});assert vote is False
agreement=[];counts={False:0,True:0}
for tri in st:
    a,b,c=[Vector(sp[i]) for i in tri];center=(a+b+c)/3;normal=(b-a).cross(c-a).normalized()
    for sign in [-1,1]:
        p=center+normal*(.0002*sign);nearest=tree.find_nearest(p)[3];old=inside(tree,p)
        if old is None or nearest<1e-6 or counts[old]>=4:continue
        new,winding=classify_winding(sp,st,p,nearest)
        agreement.append({'point':list(p),'nearest_m':nearest,'two_ray_inside':old,'winding_inside':new,'winding':winding})
        assert new==old,'SOLID_CLASSIFIER_DISAGREEMENT';counts[old]+=1
    if counts=={False:4,True:4}:break
assert counts=={False:4,True:4}
save(folder/'classification-preflight.json',{'actual_sword_surface':certification,'actual_unknown_transformation_checks':transformation_checks,
 'known_inside_outside_crosscheck':agreement,'source_geometry_unchanged':True,'original_diagnostic_float_subtraction':'historical Mathutils-before-cast; newmethodcastspositionsseparatelyfirst'})
for i,frame in enumerate(expected['frames']):
    scene.frame_set(int(frame),subframe=float(frame-int(frame)));bpy.context.view_layer.update()
    self_report,points=grip.capture(ob,rig,rest,'frame-'+str(frame),[],ww)
    contact=certified_contacts(ob,weapon,rig,contract['pads'],'frame-'+str(frame),{'frame':float(frame)})
    hp,_,_=evaluated(ob);wp,_,_=evaluated(weapon)
    he=float(np.max(np.linalg.norm(np.array(hp)-expected['hand'][i],axis=1)));we=float(np.max(np.linalg.norm(np.array(wp)-expected['weapon'][i],axis=1)))
    max_hand=max(max_hand,he);max_weapon=max(max_weapon,we);assert he<1e-6 and we<1e-6
    required=frame>=31
    admissible=not self_report['transverse_pairs'] and not self_report['degenerate_triangles'] and not contact['transverse_crossings_count'] and not contact['unknown_inside'] and contact['maximum_penetration_m']<=.001 and self_report['minimum_edge_ratio']>=.25 and self_report['maximum_edge_stretch']<=3
    row={'frame':float(frame),'contact_required':bool(required),'pass':bool(admissible and (not required or contact['surface_gate_pass'])),
       'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'original_two_ray_unknown':len(contact['original_two_ray_report']['unknown_inside']),
       'remaining_unknown':len(contact['unknown_inside']),'supplemental':contact['supplemental_classifications'],'depth_m':contact['maximum_penetration_m'],
       'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'same_saved_hand_max_m':he,'same_saved_weapon_max_m':we,
       'original_contact_report':contact['original_two_ray_report']}
    rows.append(row)
    with (folder/'interval-events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
    if i%20==0:print('CERTIFY_PROGRESS '+str({'sample':i,'frame':frame,'pass':row['pass'],'unknown_before':row['original_two_ray_unknown']}),flush=True)
ok=all(row['pass'] for row in rows)
dest=out/'right_hand_grasp_61f.blend';shutil.copyfile(ROOT/start['source']['path'],dest);assert artifact(dest)['sha256']==start['source']['sha256']
scene.frame_set(31);glb=None;structure=None
if ok:
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
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),'glb':artifact(glb) if glb else None,
 'interval_numeric_pass':ok,'samples':len(rows),'required_grasp_samples':sum(r['contact_required'] for r in rows),'original_ray_ambiguity_samples':sum(bool(r['original_two_ray_unknown']) for r in rows),
 'supplemental_classifications':sum(len(r['supplemental']) for r in rows),'first_failure':next((r for r in rows if not r['pass']),None),
 'fresh_saved_hand_max_delta_m':max_hand,'fresh_saved_weapon_max_delta_m':max_weapon,'point_tolerance_m':1e-6,
 'geometry_animation_byteidentical':True,'measurement_method_not_geometry_improvement':True,'original_v003_failure_preserved':True,
 'new_credits':0,'freshGLB':'pending','full300_art_delivery':'not_passed'})
print('R010_V004 '+str({'numeric_pass':ok,'samples':len(rows),'exported':bool(glb),'shape_changed':False}),flush=True)
