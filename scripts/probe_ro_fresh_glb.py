"""Fresh import metadata only, before validating exported vertex identity."""
from pathlib import Path
import sys,bpy,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
result=read(QA/'v004-certified-animation/combined-export.json');assert artifact(ROOT/result['artifact']['path'])==result['artifact']
bpy.context.scene.render.fps=60
bpy.ops.import_scene.gltf(filepath=str(ROOT/result['artifact']['path']),disable_bone_shape=True)
objects=[]
for ob in bpy.data.objects:
    if ob.name.startswith(('SM_RO_','ARM_RO_')):
        row={'name':ob.name,'type':ob.type,'world':[list(r) for r in ob.matrix_world]}
        if ob.type=='MESH':row.update(vertices=len(ob.data.vertices),attributes=[{'name':a.name,'type':a.data_type,'domain':a.domain} for a in ob.data.attributes],keys=[k.name for k in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else [])
        if ob.animation_data and ob.animation_data.action:row['action_range']=list(ob.animation_data.action.frame_range)
        if ob.type=='MESH' and ob.data.shape_keys and ob.data.shape_keys.animation_data and ob.data.shape_keys.animation_data.action:row['morph_action_range']=list(ob.data.shape_keys.animation_data.action.frame_range)
        objects.append(row)
save(QA/'v004-certified-animation/fresh-glb-metadata.json',{'subject':result['artifact'],'objects':objects,'scene_fps':bpy.context.scene.render.fps})
print(json.dumps(objects))
