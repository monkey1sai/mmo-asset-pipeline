"""Dependent combined diagnostic after signed isolated coordinator view review."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
start=read(QA/'v002-start.json');result=read(QA/'v002-direction/result.json')
assert result['direction_gate'] and result['numeric_self_gate']
assert not (QA/'v002-isolated-review.json').exists()
review={'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'reviewer':'Coordinator actual signed .30 side/back and positivepalm plusaxial±.15views; independent architecture review requested separately',
 'isolated_local_function_judgment':'Sufficient for dependent .15/.30 combined diagnosis. Thumbtips/thenar continuous without largecollapse in observed extremes; not grip/largecurl/art acceptance.',
 'facts':'8 frozen-pad signed direction checks pass;23actualposes transverse0/degenerate0;coords/faces/UVs/bones/fourfinger fixed.',
 'limits':'Other small signed angles numeric only; allplane convexsection includes otherfingers and cannot prove thenarvolume; ratios someCMC regress despite reducedabsoluteextension.',
 'material_gate':False,'whole_character_accepted':False,'combined_allowed':True}
save(QA/'v002-isolated-review.json',review)
folder=QA/'v002-combined';assert not folder.exists();folder.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);ww=weights(ob)
ob.data.materials.clear();ob.data.materials.append(material('r008CombinedGray',(.55,.55,.55)))
events=[]
for a in [.15,.30]:
    label=f'combined{a:.2f}';params=combined_parameters(a)
    event,pts=actual(ob,rig,rest,label,params,ww);events.append(event);render(folder,label)
params=combined_parameters(.30)
params[12]['mode']='flexion'
# Compose axial opposition withCMC flexion explicitly, preserving both rotations.
pose(rig,params)
pb=rig.pose.bones['thumb_01'];bone=rig.data.bones['thumb_01'];native=bone.matrix_local.to_3x3();axis=(bone.tail_local-bone.head_local).normalized()
curl=pb.rotation_quaternion.to_matrix()
pb.rotation_quaternion=(native.inverted()@Matrix.Rotation(-.15,3,axis)@native@curl).to_quaternion()
bpy.context.view_layer.update()
# actual() resets pose, so composite needs a declared mode and shared helper support.
# Capture via helper temporarily preserving matrix_basis through a readback hook.
saved_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
import ro_weight_vector_common as common
original_pose=common.pose
def restore_pose(rig,parameters):
    for n,m in saved_basis.items():rig.pose.bones[n].matrix_basis=m
    bpy.context.view_layer.update()
common.pose=restore_pose
try:
    event,pts=common.actual(ob,rig,rest,'combined030-opposition015',params+[{'bone':'thumb_01','angle':.15,'mode':'composed_opposition_ulnar'}],ww)
finally:common.pose=original_pose
events.append(event);render(folder,'combined030-opposition015')
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'events':events,'actual_pose_matrices':{n:[list(row) for row in m] for n,m in saved_basis.items()},
 'numeric_self_gate':all(not e['transverse_pairs'] and not e['degenerate_triangles'] for e in events),
 'visual_gate':'pending actualcombinedviews','material_gate':False,'grip_started':False,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R008_COMBINED '+json.dumps([(e['label'],e['transverse_pairs'],e['maximum_edge_stretch'],e['maximum_absolute_edge_change_m']) for e in events]))
