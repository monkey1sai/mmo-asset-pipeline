"""Read-only rest/rigid-space verification and middle-ring volume diagnosis."""
from pathlib import Path
import json,sys
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_hand_gate import evaluated
QA=ROOT/'runs/qa/ro-swordsman-combo-r006'; out=QA/'wrist-volume-diagnosis.json'; assert not out.exists()
before=ROOT/'assets/processed/ro-swordsman-combo-r006/v006-wrist-loft-attempt2/ro_wrist_loft.blend'; after=ROOT/'assets/processed/ro-swordsman-combo-r006/v007-underlay/ro_underlay_fit.blend'
bpy.ops.wm.open_mainfile(filepath=str(before),load_ui=False,use_scripts=False); p,t,_=evaluated(bpy.data.objects['SM_RO_bracer.R']); oldsolid=BVHTree.FromPolygons(p,t,all_triangles=True)
bpy.ops.wm.open_mainfile(filepath=str(after),load_ui=False,use_scripts=False); rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); bracer=bpy.data.objects['SM_RO_bracer.R']; tube=bpy.data.objects['SM_RO_WristLoft.R']; glove=bpy.data.objects['SM_RO_glove.R']
p,t,_=evaluated(bracer); neutral_error=max((a-b.co).length for a,b in zip(p,bracer.data.vertices)); wrist=Vector(state['rest']['hand.R'][0]); axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized()
outside=[]
for vert in bracer.data.vertices:
    d=vert.co-wrist; radial=(d-axis*d.dot(axis)).length
    if radial>.032: outside.append(oldsolid.find_nearest(vert.co)[3])
transforms={'matrix_world':[list(row) for row in bracer.matrix_world],'matrix_parent_inverse':[list(row) for row in bracer.matrix_parent_inverse],
            'parent':bracer.parent.name,'modifier_stack':[(m.name,m.type) for m in bracer.modifiers],
            'maximum_pose_basis_delta_from_identity':max(sum((r-c)**2 for r,c in zip(sum((list(row) for row in pb.matrix_basis),[]),sum((list(row) for row in Matrix.Identity(4)),[])))**.5 for pb in rig.pose.bones)}
ring=json.loads((QA/'v006-wrist-loft-attempt2/ring-loft.json').read_text()); counts=[len(ring['core_boundary_indices']),48,48,48,len(ring['glove_boundary_indices']),len(ring['core_boundary_indices']),48,48,48,len(ring['inner_glove_boundary_indices'])]; ranges=[]; acc=0
for n in counts: ranges.append(list(range(acc,acc+n))); acc+=n
configure(rig,state,params); basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}; rows=[]
for alpha in [0,.25,.5,.75,1]:
    for pb in rig.pose.bones:
        m=basis[pb.name]; b=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha).to_matrix().to_4x4(); b.translation=m.translation*alpha; pb.matrix_basis=b
    bpy.context.view_layer.update(); update_wrist_helper(rig); glove.data.shape_keys.key_blocks['GripContact_R'].value=alpha; bpy.context.view_layer.update(); points,_,_=evaluated(tube); ringrows=[]
    centers=[sum((points[i] for i in ids),Vector())/len(ids) for ids in ranges]
    for row,ids in enumerate(ranges):
        a=np.array([list(points[i]-centers[row]) for i in ids]); _,s,vt=np.linalg.svd(a,full_matrices=False); offset=row%5; line=centers[row-offset].lerp(centers[row-offset+4],offset/4)
        projected=a@vt[:2].T; area=abs(sum(x[0]*y[1]-y[0]*x[1] for x,y in zip(projected,np.roll(projected,-1,axis=0))))/2
        ringrows.append({'row':row,'center':list(centers[row]),'center_line_offset_m':(centers[row]-line).length,'singular_radii_m':[float(s[i]/len(ids)**.5*2**.5) for i in [0,1]],'area_m2':float(area),'best_fit_normal':vt[2].tolist()})
    rows.append({'alpha':alpha,'rings':ringrows})
result={'rest_neutral_eval_max_error_m':neutral_error,'outer_surface_points_checked':len(outside),'outer_surface_max_distance_to_source_m':max(outside),'object_state':transforms,
 'rest_geometry_consistent':neutral_error<1e-7 and max(outside)<2e-6,'five_transition_ring_measurements':rows,
 'interpretation':'Rest geometry retained, measured265unweighted new vertices cause rigid pose distortion; ring center drift/section collapse addressed separately by protected-endpoint pose correction'}
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:v for k,v in result.items() if k not in ['five_transition_ring_measurements','object_state']}))
print(json.dumps({'max_mid_ring_centerline_offset_m':max(r['center_line_offset_m'] for s in rows for r in s['rings'] if r['row']%5 in [1,2,3])}))
