"""One whole-pulp brush candidate, inverse LBS to a reversible shape key."""
from datetime import datetime,timezone
from pathlib import Path
import sys,json,bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated,contacts
from ro_pose_corrective_math import inverse_delta,smoothstep,surface_limited_magnitude
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
start=read(QA/'v002-start.json');contract=read(QA/'local-contract.json');folder=QA/'v002-pulp-corrective';folder.mkdir()
out=ROOT/'assets/processed/ro-swordsman-combo-r010/v002-pulp-corrective';out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
assert len(ob.modifiers)==1 and ob.modifiers[0].type=='ARMATURE' and not ob.modifiers[0].use_deform_preserve_volume
assert ob.data.shape_keys is None
rest=common.geometry(ob);ww=common.weights(ob);oldpose=read(ROOT/'runs/qa/ro-swordsman-combo-r009/v004-collision-constraints/result.json')
points,tris,_=evaluated(ob);sp,st,_=evaluated(sword)
root=rig.pose.bones['sword'].head;axis=(rig.pose.bones['sword'].tail-root).normalized()
handle=BVHTree.FromPolygons(sp,[t for t in st if -.112<=(sum((sp[j] for j in t),Vector())/3-root).dot(axis)<=.085],all_triangles=True)
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();normals=[v.normal.copy() for v in me.vertices];ev.to_mesh_clear()
matrices={n:np.array([list(row) for row in rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted()]) for n in rig.pose.bones.keys()}
skin={i:sum((weight*matrices[n] for n,weight in weights.items()),np.zeros((4,4))) for i,weights in ww.items()}
preflight=max(np.linalg.norm((skin[i]@np.array([*p,1.]))[:3]-np.array(points[i])) for i,p in enumerate(rest['points']))
assert preflight<1e-6,'ACTUAL_SKIN_RECONSTRUCTION_FAILED'
chains={n:[rig.data.bones[f'{n}_{j:02}'].head_local.copy() for j in range(1,4)]+[rig.data.bones[f'{n}_03'].tail_local.copy()] for n in start['branches']}
def axial(point,chain):
    rows=[];offset=0.
    for j,(a,b) in enumerate(zip(chain,chain[1:])):
        length=(b-a).length;direction=(b-a)/length;s=(point-a).dot(direction);clamped=max(0,min(length,s))
        rows.append(((point-a-direction*clamped).length,offset+clamped));offset+=length
    return min(rows)[1]/offset
ob.shape_key_add(name='Basis');key=ob.shape_key_add(name=start['shape_key_name']);key.value=0
field=[];expected={};protected=set(contract['thumb_protected_ids'])
for branch in start['branches']:
    for i in contract['corrective_body_domains'][branch]:
        assert i not in protected
        vertex=ob.data.vertices[i];p=vertex.co.copy();palmar=max(0.,-vertex.normal.y)
        amount=start['maximum_requested_posed_m']*smoothstep(.20,.65,axial(p,chains[branch]))*smoothstep(0,.5,palmar)
        hit,hn,face,gap=handle.find_nearest(points[i]);toward=(hit-points[i]).normalized()
        direction=normals[i].normalized();alignment=direction.dot(toward)
        magnitude=surface_limited_magnitude(amount,gap,alignment,start['minimum_clearance_m'])
        if magnitude<1e-10:continue
        desired=np.array(direction)*magnitude
        delta,condition=inverse_delta(skin[i][:3,:3],desired,contract['corrective_displacement_limits']['inverse_skin_condition_max'])
        assert np.linalg.norm(delta)<=contract['corrective_displacement_limits']['rest_max_m']
        key.data[i].co=p+Vector(delta)
        expected[i]=desired
        field.append({'id':i,'branch':branch,'axial_fraction':axial(p,chains[branch]),'palmar_factor':palmar,'original_gap_m':gap,
            'requested_m':amount,'applied_posed_m':magnitude,'skin_condition':condition,'rest_delta':delta.tolist(),'desired_posed_delta':desired.tolist()})
assert field
key.value=1;bpy.context.view_layer.update();newpts,_,_=evaluated(ob)
roundtrip=max((newpts[i]-points[i]-Vector(d)).length for i,d in expected.items());assert roundtrip<1e-6
outside=set(range(len(points)))-set(expected)
extra=max((newpts[i]-points[i]).length for i in outside);assert extra<1e-7
assert all(key.data[i].co==ob.data.vertices[i].co for i in protected)
self_report,pts=grip.capture(ob,rig,rest,'pulp-corrective',oldpose['controls'],ww)
contact=contacts(ob,sword,rig,contract['pads'],'pulp-corrective',{'key':start['shape_key_name'],'value':1})
gate=not self_report['transverse_pairs'] and not self_report['degenerate_triangles'] and contact['surface_gate_pass'] and self_report['minimum_edge_ratio']>=.25 and self_report['maximum_edge_stretch']<=3
key.value=0;bpy.context.view_layer.update();neutralpts,_,_=evaluated(ob)
zero_error=max((a-b).length for a,b in zip(neutralpts,points));assert zero_error<1e-7
key.value=1;bpy.context.view_layer.update()
save(folder/'corrective-field.json',{'field':field,'geometry_source':artifact(QA/'baseline/mesh-and-weights.json'),'skin_reconstruction_max_m':float(preflight),
 'inverse_roundtrip_max_m':roundtrip,'zero_key_source_pose_max_m':zero_error,'outside_additional_max_m':extra,'protected_thumb_zero_offsets':True,
 'max_rest_delta_m':max(np.linalg.norm(r['rest_delta']) for r in field),'max_posed_delta_m':max(r['applied_posed_m'] for r in field),
 'all_body_surface_not_pad_selection':True,'original_pads_unchanged':True})
save(folder/'posed-points.json',{'points':[list(p) for p in pts]})
ob.data.materials.clear();ob.data.materials.append(common.material('r010CorrectiveGray',(.55,.55,.55)))
dest=out/'right_hand_grasp_corrective.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
common.render(folder,'corrected')
assert common.geometry(ob)==rest and common.weights(ob)==ww
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'artifact':artifact(dest),'source':start['source'],'self':self_report,'contact':contact,
 'numeric_gate':gate,'shape_key':start['shape_key_name'],'field':artifact(folder/'corrective-field.json'),'raw_points':artifact(folder/'posed-points.json'),
 'basis_geometry_UV_weights_unchanged':True,'controls_source':artifact(ROOT/'runs/qa/ro-swordsman-combo-r009/v004-collision-constraints/result.json'),
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))],'new_credits':0,'interval_and_export':'pending_preflight'})
print('R010_V002 '+str({'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'numeric_gate':gate,'field_points':len(field),'max_delta':max(r['applied_posed_m'] for r in field)}))
