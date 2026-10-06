"""Read-only pose hypothesis: swing front cloth clear of crouching knees."""
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
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pose functions>','exec'),globals())
pose(1,.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75))
pb=rig.pose.bones['tabard'];m=pb.matrix.copy();m=m@Matrix.Rotation(-.65,4,'X');pb.matrix=m;bpy.context.view_layer.update()
folder=ROOT/'runs/qa/ro-swordsman-combo-r003/v001/tabard-motion-probe';folder.mkdir(exist_ok=False)
scene.render.resolution_x=scene.render.resolution_y=960
for view in ['front','side','back','three-quarter']:
    camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
report={'subject_sha256':sha,'pose':'deep-crouch','changed_geometry':False,'changed_weights':False,'tabard_local_x_radians':-.65,
        'hypothesis':'Front cloth follows authored swing as knees advance; no inference of collision pass from a bone angle.',
        'saved_master':False,'acceptance':'Actual views required; independent cloth/leg issues remain.'}
(folder/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');assert sha==hashlib.sha256(path.read_bytes()).hexdigest();print(json.dumps(report))
