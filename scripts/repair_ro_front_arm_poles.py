"""Same v001: forward elbow poles and source-verified hand influence cleanup."""
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
source=out/'ro_swordsman_reach_preflight.blend';target=out/'ro_swordsman_preflight_final.blend';assert not target.exists()
sha=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data;body=bpy.data.objects['SM_RO_SourcePreservedBody']
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
for filename,names in [('build_ro_apose_candidate.py',{'assign','dist_segment','solve','matrix','pose'}),('finish_ro_apose_preflight.py',{'orient_hand','functional_pose','contacts'})]:
    tree=ast.parse((ROOT/'scripts'/filename).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if filename=='build_ro_apose_candidate.py':
        for node in nodes:
            if node.name!='pose':continue
            modified=0
            for call in ast.walk(node):
                if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='solve' and isinstance(call.args[-1],ast.Tuple) and isinstance(call.args[-1].elts[0],ast.BinOp):
                    call.args[-1]=ast.parse('(s*.65,-.7,-.1)',mode='eval').body;modified+=1
            assert modified==1
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<same v001 measured pole correction>','exec'),globals())
source_pose=pose
groups={s:{d:[] for d in ['thumb']+['finger'+str(i) for i in range(1,5)]} for s in ['L','R']};cleaned=0
for v in body.data.vertices:
    ws={body.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}
    dominant=max(ws,key=ws.get)
    if dominant.startswith(('hand.','finger','thumb.')):
        legal={n:w for n,w in ws.items() if n.startswith(('hand.','finger','thumb.'))}
        if sum(legal.values())>.5 and abs(v.co.x)>.30 and .68<v.co.z<1.02:
            if set(ws)!=set(legal):assign(v,legal);cleaned+=1
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
    center=functional_pose(frame,h,rh,lh,sd,dual);folder=qa/'preflight-final'/name;folder.mkdir(parents=True,exist_ok=False)
    rows.append({'pose':name,'dual_grip':dual,'actual_surface_contact':contacts()})
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    for label,offset in [('grip-palm',(-.8,-1,.2)),('grip-back',(.8,.7,.3))]:
        camera((tuple(center+Vector(offset)),tuple(center),.48));scene.render.filepath=str(folder/(label+'.png'));bpy.ops.render.render(write_still=True)
functional_pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95));render_views(qa/'final-views');camera()
bpy.ops.wm.save_as_mainfile(filepath=str(target));bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target.with_suffix('.glb')),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
assert sha==hashlib.sha256(source.read_bytes()).hexdigest()
report={'same_trial':'v001','started_utc':json.loads((qa.parent/'v001-start.json').read_text())['started_utc'],'source_sha256':sha,'poses':rows,
        'changed_source_coordinates_UV':False,'hand_region_cross_arm_weights_cleaned':cleaned,'elbow_pole':'Side*.65 / forward-.7 / down-.1',
        'full_animation':False,'VFX':False,'acceptance':'Needs actual final preflight, fresh import and quality review; do not infer grasp/collision from target math.'}
(qa/'final-preflight-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='poses'}))
