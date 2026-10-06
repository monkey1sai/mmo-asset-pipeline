"""Finish the current unreviewed v003 motion, preserving the failed attempt."""
import ast
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import render_views,camera
out=ROOT/'assets/processed/ro-swordsman-combo-r002/v003';qa=ROOT/'runs/qa/ro-swordsman-combo-r002/v003'
archive=out/'attempt03-motion';archive.mkdir(exist_ok=False)
before={}
for name in ['ro_swordsman_master.blend','ro_swordsman_combo.glb','ro_skill_effects.glb']:
    before[name]=hashlib.sha256((out/name).read_bytes()).hexdigest();shutil.copy2(out/name,archive/name)
for name in ['construction-check.json','fresh-import.json']:
    shutil.copy2(qa/name,archive/name)
bpy.ops.wm.open_mainfile(filepath=str(out/'ro_swordsman_master.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman'];char=bpy.data.collections['COL_Character'];effects=bpy.data.collections['COL_SkillEffects'];scene=bpy.context.scene
for script,names in [('build_ro_swordsman.py',{'solve','bone_matrix','POSES'}),('rebuild_ro_articulation.py',{'REST','PARENTS','pose'})]:
    tree=ast.parse((ROOT/'scripts'/script).read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets) or script=='rebuild_ro_articulation.py' and isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and any(isinstance(x,ast.Name) and x.id=='side' for x in n.target.elts)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<inspected current pose mathematics>','exec'),globals())
for frame in range(1,301):
    scene.frame_set(frame)
    for first,last in zip(POSES,POSES[1:]):
        if first[0]<=frame<=last[0]:
            t=(frame-first[0])/(last[0]-first[0]);t=t*t*(3-2*t)
            target=[frame]+[first[i]+(last[i]-first[i])*t if isinstance(first[i],(int,float)) else tuple(Vector(first[i]).lerp(Vector(last[i]),t)) for i in range(1,len(first))]
            pose(frame,target,key=True);break
for fc in rig.animation_data.action.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR'
effects.hide_render=True;render_views(qa)
scene.render.resolution_x=scene.render.resolution_y=640
for f in [1,25,50,75,100,120,145,170,195,220,255,300]:
    scene.frame_set(f);camera();scene.render.filepath=str(qa/f'pose_{f:04d}.png');bpy.ops.render.render(write_still=True)
effects.hide_render=False
for f in [120,211,240]:
    scene.frame_set(f);camera(((2.8,-4,2),(0,0,1.1),3.3));scene.render.filepath=str(qa/f'effects_{f:04d}.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1);camera();bpy.ops.wm.save_as_mainfile(filepath=str(out/'ro_swordsman_master.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in char.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(out/'ro_swordsman_combo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_yup=True,export_anim_slide_to_zero=True,export_skins=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
assert hashlib.sha256((out/'ro_skill_effects.glb').read_bytes()).hexdigest()==before['ro_skill_effects.glb']
report={'candidate':'v003','same_trial_clock':True,'cause':'First all300stress found28blade/head overlap frames and125mm right wrist one-frame step. Shared grip arc moved ahead of face; continuous cross-product hand direction removes hard global-X sign flip. No geometry rebuild or new paid generation.','before':before,'after':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in before},'failed_stress':'runs/qa/ro-swordsman-combo-r002/v003/neutral-master/report.json','motion_source_sha256':hashlib.sha256((ROOT/'scripts/rebuild_ro_articulation.py').read_bytes()).hexdigest(),'acceptance':'pending rerun and independent review'}
(qa/'motion-correction.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_MOTION_REPAIRED '+json.dumps(report))
