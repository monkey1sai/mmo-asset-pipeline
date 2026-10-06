"""Fresh GLB skin/morph interval readback using exported original point IDs."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import sys,json,bpy,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_certified_grasp_gate import certified_contacts
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
result=read(QA/'v004-certified-animation/exact-weights-export.json');contract=read(QA/'local-contract.json')
folder=QA/'v004-fresh-glb-attempt3';folder.mkdir();expected=np.load(ROOT/read(QA/'v004-start.json')['expected_points']['path'])
assert artifact(ROOT/result['artifact']['path'])==result['artifact']
scene=bpy.context.scene;scene.render.fps=60
bpy.ops.import_scene.gltf(filepath=str(ROOT/result['artifact']['path']),disable_bone_shape=True)
hand=next(o for o in bpy.data.objects if o.type=='MESH' and '_R010_ID' in o.data.attributes)
weapon=next(o for o in bpy.data.objects if o.type=='MESH' and '_R010_WEAPON_ID' in o.data.attributes)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'sword' in o.pose.bones)
assert list(rig.animation_data.action.frame_range)==[1.,61.]
assert hand.data.shape_keys and hand.data.shape_keys.animation_data and hand.data.shape_keys.animation_data.action
assert list(hand.data.shape_keys.animation_data.action.frame_range)==[1.,61.]
assert any(m.type=='ARMATURE' and m.object==rig for m in hand.modifiers)
assert any(m.type=='ARMATURE' and m.object==rig for m in weapon.modifiers)
assert all({weapon.vertex_groups[g.group].name:round(g.weight,6) for g in v.groups}=={'sword':1.} for v in weapon.data.vertices)

def canonical(ob,name,count):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    attribute=mesh.attributes[name];ids=[]
    for row in attribute.data:
        integer=round(row.value);assert abs(integer-row.value)<1e-5 and 0<=integer<count;ids.append(integer)
    points=[None]*count;duplicate_error=0.
    for v,i in zip(mesh.vertices,ids):
        point=ev.matrix_world@v.co
        if points[i] is None:points[i]=point.copy()
        else:duplicate_error=max(duplicate_error,(point-points[i]).length)
    assert all(p is not None for p in points) and duplicate_error<1e-6
    triangles=[tuple(ids[i] for i in t.vertices) for t in mesh.loop_triangles]
    assert all(len(set(t))==3 for t in triangles)
    ev.to_mesh_clear()
    return points,triangles,duplicate_error

def proxy(name,points,triangles,with_ids=False):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],triangles);mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.hide_render=True
    if with_ids:
        attr=mesh.attributes.new('r007_original_point_id','INT','POINT')
        for i,row in enumerate(attr.data):row.value=i
    return obj

scene.frame_set(1);bpy.context.view_layer.update()
hp,ht,hd=canonical(hand,'_R010_ID',904);wp,wt,wd=canonical(weapon,'_R010_WEAPON_ID',1493)
assert len(ht)==1788 and len(wt)==2552
hand_proxy=proxy('QA_SourceID_Hand',hp,ht,True);sword_proxy=proxy('QA_SourceID_Sword',wp,wt)
rest=read(QA/'baseline/mesh-and-weights.json')['geometry'];rest['faces']=[list(t) for t in ht]
bind_matrix=(rig.matrix_world@rig.pose.bones['sword'].matrix).copy()
save(folder/'identity-mapping.json',{'subject':result['artifact'],'hand_mesh':hand.name,'weapon_mesh':weapon.name,
 'exported_hand_vertices':len(hand.data.vertices),'canonical_hand_sourceIDs':904,'exported_weapon_vertices':len(weapon.data.vertices),'canonical_weapon_sourceIDs':1493,
 'triangles':[len(ht),len(wt)],'mapping':'Originalexported IDs collapse UV/normal split duplicates only; no spatial posed weld, averaging, repair or retriangulation.',
 'duplicate_max_m':[hd,wd],'sourceID_duplicate_tolerance_m':1e-6,'animation_ranges':[list(rig.animation_data.action.frame_range),list(hand.data.shape_keys.animation_data.action.frame_range)]})
events=[];maximum_hand=0.;maximum_weapon=0.;maximum_bone_follow=0.;maximum_duplicate=0.;squared=0.;point_count=0
for i,frame in enumerate(expected['frames']):
    scene.frame_set(int(frame),subframe=float(frame-int(frame)));bpy.context.view_layer.update()
    hp,triangles,hd=canonical(hand,'_R010_ID',904);wp,sword_triangles,wd=canonical(weapon,'_R010_WEAPON_ID',1493)
    assert triangles==ht and sword_triangles==wt
    he=np.linalg.norm(np.array(hp)-expected['hand'][i],axis=1);we=np.linalg.norm(np.array(wp)-expected['weapon'][i],axis=1)
    maximum_hand=max(maximum_hand,float(he.max()));maximum_weapon=max(maximum_weapon,float(we.max()));maximum_duplicate=max(maximum_duplicate,hd,wd)
    squared+=float(np.sum(he*he));point_count+=len(he)
    transform=rig.matrix_world@rig.pose.bones['sword'].matrix@bind_matrix.inverted()
    follow=max((p-transform@Vector(q)).length for p,q in zip(wp,expected['weapon'][0]));maximum_bone_follow=max(maximum_bone_follow,follow)
    world_bone=SimpleNamespace(head=transform@Vector(expected['sword_head'][0]),tail=transform@Vector(expected['sword_tail'][0]))
    frame_rig=SimpleNamespace(matrix_world=Matrix.Identity(4),pose=SimpleNamespace(bones={'sword':world_bone}))
    for v,p in zip(hand_proxy.data.vertices,hp):v.co=p
    for v,p in zip(sword_proxy.data.vertices,wp):v.co=p
    hand_proxy.data.update();sword_proxy.data.update();bpy.context.view_layer.update()
    self_report,_=grip.capture(hand_proxy,rig,rest,'glb-'+str(frame),[],None)
    contact=certified_contacts(hand_proxy,sword_proxy,frame_rig,contract['pads'],'glb-'+str(frame),{'frame':float(frame),'source_ids':True})
    required=frame>=31
    admissible=not self_report['transverse_pairs'] and not self_report['degenerate_triangles'] and not contact['transverse_crossings_count'] and not contact['unknown_inside'] and contact['maximum_penetration_m']<=.001 and self_report['minimum_edge_ratio']>=.25 and self_report['maximum_edge_stretch']<=3
    ok=admissible and (not required or contact['surface_gate_pass']) and he.max()<1e-6 and we.max()<1e-6 and follow<1e-6
    row={'frame':float(frame),'pass':bool(ok),'contact_required':bool(required),'hand_max_m':float(he.max()),'weapon_max_m':float(we.max()),'weapon_bone_follow_m':follow,
      'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'depth_m':contact['maximum_penetration_m'],
      'original_ray_unknown':len(contact['original_two_ray_report']['unknown_inside']),'remaining_unknown':len(contact['unknown_inside']),
      'supplemental':contact['supplemental_classifications'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()}}
    events.append(row)
    with (folder/'interval-events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
    if i%20==0:print('FRESH_GLB_PROGRESS '+str({'frame':frame,'pass':bool(ok),'hand_max_m':float(he.max())}),flush=True)
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],'fresh_process_import':True,'samples':len(events),
 'numeric_interval_pass':all(r['pass'] for r in events),'first_failure':next((r for r in events if not r['pass']),None),
 'maximum_hand_point_difference_m':maximum_hand,'hand_RMS_difference_m':(squared/point_count)**.5,'maximum_weapon_point_difference_m':maximum_weapon,
 'maximum_actual_bone_follow_error_m':maximum_bone_follow,'maximum_split_duplicate_difference_m':maximum_duplicate,'point_tolerance_m':1e-6,
 'skin_morph_same_active_clip_verified':True,'source_identity':artifact(folder/'identity-mapping.json'),'original_pad_masks_unchanged':True,
 'supplemental_samples':sum(bool(r['supplemental']) for r in events),'no_target_engine_or_full300_claim':True})
print('FRESH_GLB_RESULT '+str({'pass':all(r['pass'] for r in events),'hand_max_m':maximum_hand,'hand_rms_m':(squared/point_count)**.5,'weapon_max_m':maximum_weapon,'bone_follow_max_m':maximum_bone_follow}),flush=True)
