"""Read-only fixed-pose grip orientation test plus actual cloth-weight readback."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera
path=ROOT/'assets/processed/ro-swordsman-combo-r003/v001/ro_swordsman_continuous_base.blend'
sha=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data;body=bpy.data.objects['SM_RO_SourcePreservedBody']
old=path.with_name('ro_swordsman_hands_restored.blend')
with bpy.data.libraries.load(str(old),link=False) as (source,loaded):loaded.objects=['SM_RO_SourcePreservedBody']
native=loaded.objects[0];assert len(native.data.vertices)==len(body.data.vertices)
difference=0;count=0
for a,b in zip(native.data.vertices,body.data.vertices):
    wa={native.vertex_groups[g.group].name:g.weight for g in a.groups}
    wb={body.vertex_groups[g.group].name:g.weight for g in b.groups}
    delta=max([abs(wa.get(n,0)-wb.get(n,0)) for n in ['coat.L','coat.R','tabard']])
    difference=max(difference,delta);count+=delta>1e-7
bpy.data.objects.remove(native,do_unlink=True)
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pose functions>','exec'),globals())
poses=[('overhead',.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98)),('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75)),('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6))]
folder=ROOT/'runs/qa/ro-swordsman-combo-r003/v001/grip-frame-probe';folder.mkdir(exist_ok=False)
scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd) in enumerate(poses,1):
    pose(frame,h,rh,lh,sd)
    # Rest sword/grip axis is -Y. A continuous shortest-arc rotation carries
    # both the hand rest frame and its children to the actual sword direction.
    rotation=Vector((0,-1,0)).rotation_difference(Vector(sd).normalized()).to_matrix().to_4x4()
    pb=rig.pose.bones['hand.R'];wrist=pb.head.copy();m=rotation@arm.bones['hand.R'].matrix_local;m.translation=wrist;pb.matrix=m
    bpy.context.view_layer.update()
    hand=pb.matrix;location=hand@(arm.bones['hand.R'].matrix_local.inverted()@Vector(REST['sword'][0]))
    rig.pose.bones['sword'].matrix=matrix(location,location+Vector(sd).normalized()*.95,Vector((0,1,0)))
    pb=rig.pose.bones['tabard'];pb.matrix=pb.matrix@Matrix.Rotation(-.65*min(1,max(0,(.88-h)/.20)),4,'X')
    bpy.context.view_layer.update()
    target=folder/name;target.mkdir()
    for view in ['front','side','three-quarter']:
        camera(view);scene.render.filepath=str(target/(view+'.png'));bpy.ops.render.render(write_still=True)
report={'subject_sha256':sha,'saved_master':False,'changed_weights':False,'changed_geometry':False,
        'cloth_weight_readback':{'max_absolute_delta':difference,'vertices_different_over1e7':count,'method':'Named coat/tabard weights compared before and after top4 normalization.'},
        'hypothesis':'Hand and grip direction rotate together instead of sword axis moving inside a fixed hand orientation.',
        'acceptance':'No contact or deformation pass inferred; view actual wrist/grip/cloth.'}
(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');assert sha==hashlib.sha256(path.read_bytes()).hexdigest();print(json.dumps(report))
