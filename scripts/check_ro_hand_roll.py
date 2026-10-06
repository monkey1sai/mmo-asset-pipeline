"""Isolated forearm roll hypothesis, no geometry changes or contact search reset."""
from datetime import datetime,timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import pose
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-roll'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-roll'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-direction/direction.json').read_text()); source=ROOT/previous['artifact']['path']
if QA.exists() or OUT.exists() or hashlib.sha256(source.read_bytes()).hexdigest()!=previous['artifact']['sha256']: raise RuntimeError('Preserve roll diagnosis and source')
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-start.json').read_text())
if (datetime.now(timezone.utc)-datetime.fromisoformat(start['started_utc'])).total_seconds()>=start['prototype_deadline_seconds']: raise RuntimeError('Prototype deadline exhausted')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json']); core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']
QA.mkdir(parents=True); OUT.mkdir(parents=True); (QA/'rig-helper-used.py').write_bytes((ROOT/'scripts/ro_core_rig.py').read_bytes())
mat=bpy.data.materials.new('Diagnostic_gray_roll'); mat.use_nodes=True; mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.28,.32,.38,1); mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.7
hidden=[]
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH' and ob not in (core,sword): hidden.append((ob,ob.hide_render)); ob.hide_render=True
results={}
for method in ['before','after']:
    if method=='after': state['forearm_twist_to_palm']={'R':True}
    results[method]=pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),two_hands=False)
    deps=bpy.context.evaluated_depsgraph_get(); ev=core.evaluated_get(deps)
    ids={v.index for v in core.data.vertices if v.co.x<-.34 and v.co.z<.99}
    faces=[list(f.vertices) for f in core.data.polygons if all(i in ids for i in f.vertices)]
    mesh=bpy.data.meshes.new('Right_hand_diagnostic'); mesh.from_pydata([ev.matrix_world@v.co for v in ev.data.vertices],[],faces); mesh.materials.append(mat)
    ob=bpy.data.objects.new('Right_hand_only_diagnostic',mesh); bpy.context.scene.collection.objects.link(ob)
    for f in mesh.polygons: f.use_smooth=True
    core.hide_render=True; folder=QA/method; folder.mkdir()
    target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.65)
    for name,offset in [('front',(.30,-1,.15)),('side',(1,0,.12)),('back',(-.3,1,.12)),('underside',(0,-.25,-1))]:
        camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ob,do_unlink=True); bpy.data.meshes.remove(mesh); core.hide_render=False
for ob,value in hidden: ob.hide_render=value
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); rig['state_json']=json.dumps(state); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_roll_checked.blend'))
report={'source':previous['artifact'],'hypothesis':'Minimal-axis forearm solver did not account for hand pronation; align forearm roll with measured palm while preserving bone endpoints/geometry.',
        'diagnostic_scope':'Only actual evaluated right distal forearm/hand subset plus full sword; full core temporarily hidden to make back surface visible, original assembly unchanged.',
        'poses':results,'contact_search_count':100,'prototype_clock_reset':False,'rig_accepted':False,
        'artifact':{'path':(OUT/'ro_roll_checked.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_roll_checked.blend').read_bytes()).hexdigest()}}
(QA/'roll.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print('RO_HAND_ROLL '+json.dumps(report))
