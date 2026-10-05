"""Meet the frozen60k budget inside the same unreviewed candidate; archive first."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import render_views, camera
out=ROOT/'assets/processed/ro-swordsman-combo-r002/v003';qa=ROOT/'runs/qa/ro-swordsman-combo-r002/v003'
archive=out/'attempt02-overbudget'
if archive.exists():
    for name in ['ro_swordsman_master.blend','ro_swordsman_combo.glb','ro_skill_effects.glb']:
        assert hashlib.sha256((out/name).read_bytes()).digest()==hashlib.sha256((archive/name).read_bytes()).digest(),'Previous optimization wrote data; stop instead of overwrite'
else:
    archive.mkdir()
    for name in ['ro_swordsman_master.blend','ro_swordsman_combo.glb','ro_skill_effects.glb']:
        shutil.copy2(out/name,archive/name)
before_report=json.loads((qa/'construction-check.json').read_text());(qa/'construction-check-overbudget.json').write_text(json.dumps(before_report,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(out/'ro_swordsman_master.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.frame_set(1);char=bpy.data.collections['COL_Character'];effects=bpy.data.collections['COL_SkillEffects'];rig=bpy.data.objects['ARM_RO_Swordsman']
counts=[]
for ob in char.objects:
    if ob.type!='MESH' or not ob.name.startswith(('SM_EyeLash_','SM_EyeWhite_','SM_EyeIris_','SM_EyePupil_','SM_EyeCatchlight_')):continue
    before=sum(len(p.vertices)-2 for p in ob.data.polygons)
    bpy.context.view_layer.objects.active=ob
    bm=bmesh.new();bm.from_mesh(ob.data);boundary={v.index for e in bm.edges if e.is_boundary for v in e.verts};bm.free()
    group=ob.vertex_groups.new(name='EyeInteriorOptimization')
    group.add([v.index for v in ob.data.vertices if v.index not in boundary],1,'REPLACE')
    dec=ob.modifiers.new('InteriorBudgetReduction','DECIMATE');dec.ratio=.8;dec.vertex_group=group.name;dec.vertex_group_factor=1
    # Collapse in bind space, before armature, so current pose is never baked twice.
    while ob.modifiers.find(dec.name)>0:bpy.ops.object.modifier_move_up(modifier=dec.name)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    remove=ob.vertex_groups.get('EyeInteriorOptimization')
    if remove:ob.vertex_groups.remove(remove)
    after=sum(len(p.vertices)-2 for p in ob.data.polygons);counts.append({'mesh':ob.name,'before':before,'after':after,'boundary_vertices_protected':len(boundary)})
total=sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in char.objects if ob.type=='MESH')
if total>60000:raise RuntimeError('Frozen triangle budget still exceeded; archive preserved')
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
before_report['triangles_character']=total;before_report['optimization_report']='eye-budget-optimization.json'
(qa/'construction-check.json').write_text(json.dumps(before_report,indent=2)+'\n')
(qa/'eye-budget-optimization.json').write_text(json.dumps({'cause':'Actual geometry60780tri exceeded frozen60000. Only dense thin eye-surface interior reduced; rim protected, rig/contact/motion unchanged. Full and original overbudget artifacts preserved before correction; same v003 clock, no new candidate or generation.', 'before':60780,'after':total,'meshes':counts,'master_sha256':hashlib.sha256((out/'ro_swordsman_master.blend').read_bytes()).hexdigest()},indent=2)+'\n')
print('BUDGET_OPTIMIZED '+str(total))
