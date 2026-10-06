"""Repair exporter grouping only; retain first uncoupled GLB and its evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,struct,sys,bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
folder=QA/'v004-certified-animation';result=read(folder/'result.json');assert result['interval_numeric_pass']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
properties=bpy.ops.export_scene.gltf.get_rna_type().properties
name='export_anim_scene_split_object';assert name in properties and properties[name].type=='BOOLEAN'
save(folder/'animation-grouping-preflight.json',{'parameter':name,'type':properties[name].type,'default':properties[name].default,
 'observed_problem':'Initial supportedSCENE export splits skeleton andmorphinto2clips','classification':'TEST_FAILURE: exporter grouping not synchronized clip',
 'old_GLb':result['glb'],'old_structure':artifact(folder/'glb-structure.json'),'curve_and_source_changed':False})
bpy.context.scene.frame_set(31)
bpy.ops.object.select_all(action='DESELECT')
for n in ['SM_RO_RightHand_Exterior','ARM_RO_HandDiagnostic','SM_RO_LocalActualSword']:bpy.data.objects[n].select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['ARM_RO_HandDiagnostic']
dest=(ROOT/result['artifact']['path']).with_name('right_hand_grasp_61f_combined.glb')
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_yup=True,export_skins=True,
 export_morph=True,export_morph_animation=True,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True,
 export_frame_range=True,export_frame_step=1,export_attributes=True,export_anim_scene_split_object=False)
blob=dest.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length].decode('utf-8'))
animations=[{'name':a.get('name'),'paths':sorted(set(c['target']['path'] for c in a['channels'])),'channels':len(a['channels'])} for a in doc.get('animations',[])]
assert len(animations)==1 and 'weights' in animations[0]['paths'] and 'rotation' in animations[0]['paths']
save(folder/'combined-export.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'artifact':artifact(dest),'source_blend':result['artifact'],
 'raw_uncoupled_export_preserved':result['glb'],'animations':animations,'skin_count':len(doc['skins']),
 'supported_parameter':{'export_anim_scene_split_object':False},'new_candidate_or_shape_search':False,'fresh_GLb':'pending'})
print('COMBINED_GLTF '+json.dumps(animations))
