"""Sign-isolated prototype readback; gray diagnostic is supplementary, not art PASS."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import curl_digits,pose
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-direction'
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-direction'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-prototype/prototype.json').read_text()); source=ROOT/previous['artifact']['path']
if QA.exists() or OUT.exists() or hashlib.sha256(source.read_bytes()).hexdigest()!=previous['artifact']['sha256']: raise RuntimeError('Preserve direction diagnosis/source')
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-start.json').read_text())
if (datetime.now(timezone.utc)-datetime.fromisoformat(start['started_utc'])).total_seconds()>=start['prototype_deadline_seconds']: raise RuntimeError('Prototype deadline exhausted')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json']); core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']
QA.mkdir(parents=True); OUT.mkdir(parents=True)
(QA/'rig-helper-used.py').write_bytes((ROOT/'scripts/ro_core_rig.py').read_bytes())
mat=bpy.data.materials.new('Diagnostic_gray_only'); mat.diffuse_color=(.28,.32,.38,1); mat.use_nodes=True; mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.28,.32,.38,1); mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.7
original_materials=list(core.data.materials)
for i in range(len(core.data.materials)): core.data.materials[i]=mat
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH' and ob not in (core,sword): ob.hide_render=True
def views(folder):
    folder.mkdir(parents=True,exist_ok=True); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.65)
    for name,offset in [('front',(.30,-1,.15)),('side',(1,0,.12)),('back',(-.3,1,.12))]:
        camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
small=dict(state); small['finger_angles']={}
curl_digits(rig,small,'R',.30); views(QA/'small-curl')
result=pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),two_hands=False); views(QA/'single-grip')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
for i,old in enumerate(original_materials): core.data.materials[i]=old
for ob in bpy.data.collections['COL_Character'].objects: ob.hide_render=False
bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_direction_checked.blend'))
report={'classification':'TEST_FAILURE','original_axis':'direction.cross(front) = -width; negative angle turns away from palm','corrected_axis':'front.cross(direction) = width; negative angle turns toward palm',
        'material_diagnosis':'Source/prototype each have one UVMap and material model. New face corners from different original UV islands interpolate across unrelated atlas regions; nearest-corner transfer is not a valid production rebake.',
        'source':previous['artifact'],'prototype_clock_reset':False,'contact_search_count':100,'gray_render_scope':'Additional unoccluded shape diagnostic only; fixed original textured quality views remain required.',
        'art_accepted':False,'artifact':{'path':(OUT/'ro_direction_checked.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_direction_checked.blend').read_bytes()).hexdigest()}}
(QA/'direction.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print('RO_HAND_DIRECTION '+json.dumps(report))
