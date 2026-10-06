"""Actual Blender direction regression check, independent of rendering/quality claims."""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-surface/axis-runtime-check.json'
if QA.exists(): raise RuntimeError('Preserve runtime direction check')
source=ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-surface/ro_surface_specimen.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json']); rows=[]
for side in ['R','L']:
    front=Vector(state['hand_frames'][side]['front'])
    for i in range(1,5):
        for joint in ('01','02','03')[:state.get('finger_joint_count',{}).get(side,2)]:
            bone=rig.data.bones[f'finger{i}.{side}_{joint}']; direction=(bone.tail_local-bone.head_local).normalized()
            axis=front.cross(direction).normalized()
            toward=(Matrix.Rotation(-.30,3,axis)@direction-direction).dot(front)
            wrong=(Matrix.Rotation(-.30,3,-axis)@direction-direction).dot(front)
            if toward<=0 or wrong>=0: raise RuntimeError('Digit direction regression: '+bone.name)
            rows.append({'bone':bone.name,'correct_axis_front_displacement':toward,'opposite_axis_front_displacement':wrong})
result={'scope':'Actual Blender matrix direction smoke check for measured bones; no geometry/deformation/contact acceptance.',
    'blender':bpy.app.version_string,'bones_checked':len(rows),'checks':rows,'status':'pass',
    'subject':{'path':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},'art_pass':False}
QA.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print('RO_AXIS_RUNTIME '+json.dumps({'bones_checked':len(rows),'status':'pass','art_pass':False}))
