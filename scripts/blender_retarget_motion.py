"""Reviewed embedded-GLB motion -> immutable target-rig copy, local bake.

Intake via art_sources remains mandatory. This PUBLIC workspace adapter does
not waive Mixamo raw-redistribution policy. Run only on approved user-owned or
otherwise admissible imported motion; Mixamo actual use stays blocked until
the human rights/storage decision and valid source output exist.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import identity
import art_sources
from rig_motion import retarget,validate_rig_document,validate_export_channels
from blender_art_preview import embedded_glb_only
from cv1_restore_glb_weights import split_glb
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
for key in ('request','receipt','source-root','motion','target','target-sha256','profile','out'):p.add_argument('--'+key,required=True)
p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,required=True);p.add_argument('--fps',type=int,default=60)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
request=identity.read_json(identity.command_path(ROOT,a.request));receipt=identity.read_json(identity.command_path(ROOT,a.receipt))
source_root=Path(a.source_root).resolve()
art_sources.validate_receipt(receipt,request,ROOT,source_root,art_sources.read_catalog(ROOT))
motion=identity.command_path(source_root,a.motion)
if not any(identity.command_path(source_root,f['path'])==motion for f in receipt['files']):raise ValueError('MOTION_NOT_IN_RECEIPT')
target=identity.command_path(ROOT,a.target);embedded_glb_only(target);embedded_glb_only(motion)
if identity.file_digest(target)!=a.target_sha256:raise ValueError('TARGET_DRIFT')
profile=identity.read_json(identity.command_path(ROOT,a.profile));mapping=profile['source_to_target']
secondary={n for names in profile['secondary_ownership'].values() for n in names}
if secondary & set(mapping.values()):raise ValueError('BONE_WRITER_CONFLICT')
if profile['root_motion_policy']!='in_place':raise ValueError('EXPLICIT_ROOT_MOTION_ADAPTER_REQUIRED')
validate_rig_document(split_glb(motion.read_bytes())[0],mapping.keys())
validate_rig_document(split_glb(target.read_bytes())[0],set(mapping.values())|secondary)
if not 0<=a.start<a.end<=10000 or not 1<=a.fps<=240:raise ValueError('FRAME_RANGE')
out=identity.command_path(ROOT,a.out)
if not out.relative_to(ROOT).as_posix().startswith('assets/processed/'):raise ValueError('OUTPUT_SCOPE')
if out.exists():raise ValueError('OUTPUT_EXISTS')
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.scene.render.fps=a.fps
bpy.ops.import_scene.gltf(filepath=str(motion),merge_vertices=False)
source_rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
if len(source_rigs)!=1:raise ValueError('SOURCE_RIG_COUNT')
source=source_rigs[0];source_objects=list(bpy.context.scene.objects)
rest={b.name:np.asarray(b.matrix_local) for b in source.data.bones}
bpy.ops.import_scene.gltf(filepath=str(target),merge_vertices=False)
target_objects=[o for o in bpy.context.scene.objects if o not in source_objects]
target_rigs=[o for o in target_objects if o.type=='ARMATURE']
if len(target_rigs)!=1:raise ValueError('TARGET_RIG_COUNT')
rig=target_rigs[0];original_rest={b.name:np.asarray(b.matrix_local) for b in rig.data.bones}
for armature in (source,rig):
    if not np.allclose(np.asarray(armature.matrix_world),np.eye(4),atol=1e-6):
        raise ValueError('ARMATURE_OBJECT_TRANSFORM_REQUIRES_REVIEWED_BASIS')
for bone in rig.pose.bones:
    bone.rotation_mode='QUATERNION'
original_parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
rig.animation_data_clear();scene=bpy.context.scene;scene.render.fps=a.fps;scene.frame_start=a.start;scene.frame_end=a.end
ordered=sorted(rig.pose.bones,key=lambda b:len(b.parent_recursive))
for frame in range(a.start,a.end+1):
    scene.frame_set(frame);bpy.context.view_layer.update()
    poses={b.name:np.asarray(b.matrix) for b in source.pose.bones}
    transfer=retarget(rest,poses,original_rest,mapping,target_parents=original_parents)
    for bone in ordered:
        bone.matrix=Matrix(transfer[bone.name].tolist());bpy.context.view_layer.update()
        if bone.name in mapping.values():
            bone.keyframe_insert('location',frame=frame-a.start);bone.keyframe_insert('rotation_quaternion',frame=frame-a.start);bone.keyframe_insert('scale',frame=frame-a.start)
if original_parents!={b.name:b.parent.name if b.parent else None for b in rig.data.bones}:raise ValueError('TARGET_CONTRACT_CHANGED')
for b in rig.data.bones:
    if not np.array_equal(np.asarray(b.matrix_local),original_rest[b.name]):raise ValueError('TARGET_REST_CHANGED')
out.mkdir(parents=True,exist_ok=False)
rig.animation_data.action.name='RETARGET_BODY_IN_PLACE'
scene.frame_start=0;scene.frame_end=a.end-a.start;scene.frame_set(0)
for source_object in source_objects:
    bpy.data.objects.remove(source_object,do_unlink=True)
for obj in bpy.context.scene.objects:obj.select_set(obj in target_objects)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(out/'retarget-local.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'retarget-local.glb'),export_format='GLB',use_selection=True,export_animations=True,export_force_sampling=False,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_anim_slide_to_zero=True)
document=split_glb((out/'retarget-local.glb').read_bytes())[0]
channels=validate_export_channels(document,mapping.values(),secondary)
for sampler in document['animations'][0]['samplers']:
    times=document['accessors'][sampler['input']]
    if abs(times['min'][0])>1e-6 or abs(times['max'][0]-(a.end-a.start)/a.fps)>1e-6:raise ValueError('EXPORT_TIME_RANGE')
result={'request_sha256':identity.json_digest(request),'profile_sha256':identity.json_digest(profile),'target_sha256':a.target_sha256,
        'source_sha256':identity.file_digest(motion),'blender':bpy.app.version_string,'target_rest_unchanged':True,
        'target_hierarchy_unchanged':True,'root_policy':'in_place','secondary_tracks_authored':False,'export_channel_check':channels,'time_rule':'(frame-start)/fps','acceptance':'NOT_RUN'}
with (out/'report.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
