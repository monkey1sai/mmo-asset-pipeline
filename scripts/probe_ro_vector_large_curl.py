"""Three fixed grey functional poses before UV work or sword fitting."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
result=read(QA/'v002-direction/result.json');small=read(QA/'v002-combined/result.json')
assert result['direction_gate'] and small['numeric_self_gate']
folder=QA/'v002-functional-curl';assert not folder.exists();folder.mkdir()
plan=[{'id':'approach','fourfinger':[.5,.7,.425],'thumb':[.15,.50,.25],'pronation':.30},
      {'id':'midgrip','fourfinger':[.8,1.05,.60],'thumb':[.25,.70,.35],'pronation':.45},
      {'id':'closedgrip','fourfinger':[.95,1.20,.65],'thumb':[.30,.80,.40],'pronation':.50}]
save(folder/'plan.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'poses':plan,
 'scope':'Fixedfunctiondiagnosis; not randomweightvariants, no sword present or contact/holdingPASS',
 'subject':result['artifact'],'gray_small_motion_local_review':'Coordinator combined .15/.30/.15axial actual side/palm/back preserves volume sufficiently for stronger function diagnosis; no overall artPASS.'})
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);ww=weights(ob);ob.data.materials.clear();ob.data.materials.append(material('r008FunctionalGray',(.55,.55,.55)))
import ro_weight_vector_common as common
events=[]
for row in plan:
    params=[{'bone':f'{branch}_{i:02}','angle':a,'mode':'flexion'} for branch in ['finger1','finger2','finger3','finger4'] for i,a in enumerate(row['fourfinger'],1)]
    params += [{'bone':f'thumb_{i:02}','angle':a,'mode':'flexion'} for i,a in enumerate(row['thumb'],1)]
    pose(rig,params)
    bone=rig.data.bones['thumb_01'];native=bone.matrix_local.to_3x3();axis=(bone.tail_local-bone.head_local).normalized();pb=rig.pose.bones['thumb_01']
    pb.rotation_quaternion=(native.inverted()@Matrix.Rotation(-row['pronation'],3,axis)@native@pb.rotation_quaternion.to_matrix()).to_quaternion()
    bpy.context.view_layer.update()
    matrices={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
    original_pose=common.pose
    def restore_pose(rig,parameters):
        for n,m in matrices.items():rig.pose.bones[n].matrix_basis=m
        bpy.context.view_layer.update()
    common.pose=restore_pose
    try:event,pts=common.actual(ob,rig,rest,row['id'],params+[{'bone':'thumb_01','angle':row['pronation'],'mode':'composed_opposition_ulnar'}],ww)
    finally:common.pose=original_pose
    event['actual_basis']={n:[list(r) for r in m] for n,m in matrices.items()};events.append(event);render(folder,row['id'])
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'events':events,'numeric_self_gate':all(not e['transverse_pairs'] and not e['degenerate_triangles'] for e in events),
 'visual_gate':'pendingactualviews','material_gate':False,'sword_or_contact_present':False,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R008_FUNCTION '+json.dumps([(e['label'],e['transverse_pairs'],e['maximum_edge_stretch'],e['minimum_edge_ratio']) for e in events]))
