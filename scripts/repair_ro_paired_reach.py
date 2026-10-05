"""Same v001: keep paired grip in both arms' reachable volume.

The previous targets clamped the left wrist in crouch/downslash. This modifies
only shared grip placement, preserving prior failures and rest geometry/weights.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera,render_views
out=ROOT/'assets/processed/ro-swordsman-combo-r003/v001';qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001'
source=out/'ro_swordsman_functional_preflight.blend';target=out/'ro_swordsman_reach_preflight.blend';assert not target.exists()
sha=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data;body=bpy.data.objects['SM_RO_SourcePreservedBody']
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
for filename,names in [('build_ro_apose_candidate.py',{'assign','dist_segment','solve','matrix','pose'}),('finish_ro_apose_preflight.py',{'orient_hand','functional_pose','contacts'})]:
    tree=ast.parse((ROOT/'scripts'/filename).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed same v001 functions>','exec'),globals())
source_pose=pose
groups={s:{d:[] for d in ['thumb']+['finger'+str(i) for i in range(1,5)]} for s in ['L','R']}
for v in body.data.vertices:
    for side in groups:
        for digit in groups[side]:
            if sum(g.weight for g in v.groups if body.vertex_groups[g.group].name.startswith(digit+'.'+side))>.5:groups[side][digit].append(v.index)
poses=[('standing',.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95),False),
       ('overhead',.88,(-.10,-.20,1.62),(.17,-.12,1.57),(0,-.2,.98),True),
       ('half-crouch',.78,(0,-.17,1.10),(.19,-.28,1.0),(-.1,-.65,.75),True),
       ('deep-crouch',.68,(0,-.16,1.02),(.19,-.28,1.0),(-.1,-.65,.75),True),
       ('downslash',.78,(0,-.18,.98),(.18,-.30,1.05),(0,-.8,-.6),True)]
rows=[];scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd,dual) in enumerate(poses,1):
    center=functional_pose(frame,h,rh,lh,sd,dual);folder=qa/'preflight-paired-reach'/name;folder.mkdir(parents=True,exist_ok=False)
    rows.append({'pose':name,'dual_grip':dual,'actual_surface_contact':contacts(),'right_target':rh})
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    camera((tuple(center+Vector((-.8,-1,.2))),tuple(center),.48));scene.render.filepath=str(folder/'grip-palm.png');bpy.ops.render.render(write_still=True)
functional_pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95));render_views(qa/'paired-reach-views');camera()
bpy.ops.wm.save_as_mainfile(filepath=str(target));bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target.with_suffix('.glb')),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
assert sha==hashlib.sha256(source.read_bytes()).hexdigest()
report={'same_trial':'v001','started_utc':json.loads((qa.parent/'v001-start.json').read_text())['started_utc'],'source_sha256':sha,'poses':rows,
        'changed_source_geometry':False,'changed_weights':False,'full_animation':False,'VFX':False,'acceptance':'Await actual preflight; no automatic contact PASS.'}
(qa/'paired-reach-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='poses'}))
