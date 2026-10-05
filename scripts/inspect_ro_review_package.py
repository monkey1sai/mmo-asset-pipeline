"""Body-only rest bounds and rig map, distinct from failed posed motion."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1];out=ROOT/'assets/processed/ro-swordsman-combo-r002/v003';qa=ROOT/'runs/qa/ro-swordsman-combo-r002/v003'
source=out/'ro_swordsman_master.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman'];rig.data.pose_position='REST';bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
points=[];pivots=[]
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type!='MESH':continue
    eo=ob.evaluated_get(graph);me=eo.to_mesh();verts=[eo.matrix_world@v.co for v in me.vertices];eo.to_mesh_clear()
    if not ob.name.startswith(('SM_Sword','SM_EmptyScabbard','SM_Scabbard')):points.extend(verts)
    pivots.append({'object':ob.name,'origin_world_m':list(ob.matrix_world.translation),'armature_parent':ob.parent.name if ob.parent else None,'binding':'vertex groups/armature bones, not independent object transform pivots'})
lo=[min(v[i] for v in points) for i in range(3)];hi=[max(v[i] for v in points) for i in range(3)]
mapping=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head_m':list(b.head_local),'tail_m':list(b.tail_local),'deform':b.use_deform} for b in rig.data.bones]
report={'subject_sha256':before,'subject_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before,'method':'Actual evaluated master in temporary REST display, exclude sword/scabbard only. Never save this diagnostic scene.','body_only_rest_bounds_m':{'min':lo,'max':hi,'height':hi[2]-lo[2]},'rig_origin_world_m':list(rig.matrix_world.translation),'pivots':pivots,'rig_mapping':mapping,'scale_pose_distinction':'Nominal body scale/rest ground placement are separate from failed posed victory foot support. No animation acceptance claimed.'}
(qa/'body-scale-rig-map.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in {'pivots','rig_mapping'}}))
