"""Fresh CLI scene import and actual local prototype skeletal/morph playback."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,struct,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_hand_gate import evaluated
from ro_review_common import stage,camera
BASE=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASE/'v008-glb-roundtrip'
assert not (QA/'roundtrip.json').exists()
if not QA.exists(): QA.mkdir()
report=json.loads((BASE/'v008-rigid-wrist/rigid-wrist.json').read_text()); item=report['artifacts'][1]; path=ROOT/item['path']; raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==item['sha256']
magic,version,length=struct.unpack_from('<4sII',raw); size,kind=struct.unpack_from('<II',raw,12); assert magic==b'glTF' and version==2 and length==len(raw) and kind==0x4e4f534a
doc=json.loads(raw[20:20+size]); assert not any(im.get('uri') for im in doc.get('images',[])); assert doc.get('animations')
times=[]
for animation in doc['animations']:
    for sampler in animation['samplers']:
        a=doc['accessors'][sampler['input']]; times.append([a.get('min',[None])[0],a.get('max',[None])[0]])
assert all(a is not None and b is not None for a,b in times)
clip_start=min(a for a,b in times); clip_end=max(b for a,b in times)
assert abs(clip_end-clip_start-1)<1e-6
# factory-startup supplies isolated defaults; only this fresh process scene is cleared.
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob,do_unlink=True)
scene=bpy.context.scene; scene.render.fps=60
bpy.ops.import_scene.gltf(filepath=str(path),disable_bone_shape=True)
meshes=[o for o in bpy.data.objects if o.type=='MESH']; rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']; assert len(rigs)==1
assert sum(len(p.vertices)-2 for ob in meshes for p in ob.data.polygons)==report['whole_triangles']
expected=json.loads((BASE/'v008-rigid-wrist/roundtrip-expected.json').read_text()); action_ranges={a.name:list(a.frame_range) for a in bpy.data.actions}; import_start=min(r[0] for r in action_ranges.values()); import_end=max(r[1] for r in action_ranges.values()); assert abs(import_end-import_start-60)<1e-5
resolved={}
for name in expected['checkpoints'][0]['objects']:
    nodes=[n for n in doc['nodes'] if n.get('name')==name and n.get('mesh') is not None]
    assert len(nodes)==1,'Exact named glTF source node absent: '+name
    gltf_mesh_name=doc['meshes'][nodes[0]['mesh']]['name']
    candidates=[ob for ob in meshes if ob.data.name==gltf_mesh_name]
    assert len(candidates)==1,'Source object must map to exactly one actual mesh: '+name
    resolved[name]=candidates[0]
assert QA.exists() and not list(QA.iterdir()),'Preserve previous partial results'
stage(); scene.frame_start=int(import_start); scene.frame_end=int(import_end); scene.render.resolution_x=scene.render.resolution_y=1280; scene.render.resolution_percentage=100; samples=[]; imported_positions={}
def distances(a,at,b,bt):
    aa=[Vector(p) for p in a]; bb=[Vector(p) for p in b]; left=BVHTree.FromPolygons(aa,at,all_triangles=True); right=BVHTree.FromPolygons(bb,bt,all_triangles=True)
    return max(max(right.find_nearest(p)[3] for p in aa),max(left.find_nearest(p)[3] for p in bb))
for checkpoint in expected['checkpoints']:
    source_frame=checkpoint['frame']; imported_frame=import_start+source_frame-1; scene.frame_set(int(imported_frame)); bpy.context.view_layer.update(); row={}
    for name,ref in checkpoint['objects'].items():
        ob=resolved[name]; points,triangles,_=evaluated(ob); error=distances(ref['positions'],ref['triangles'],points,triangles)
        row[name]={'sampled_surface_bidirectional_max_error_m':error,'source_vertices':len(ref['positions']),'imported_vertices':len(points),'pass_0_1mm':error<=.0001}
        imported_positions[(source_frame,name)]=points
    samples.append({'source_frame':source_frame,'imported_frame':imported_frame,'objects':row})
    if source_frame in [1,31,61]:
        folder=QA/f'frame-{source_frame:03d}'; folder.mkdir(); rig=rigs[0]; target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
        for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1))]:
            camera((tuple(target+Vector(offset)),tuple(target),.29)); scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
motion={}
for name in expected['checkpoints'][0]['objects']:
    first=imported_positions[(1,name)]; last=imported_positions[(61,name)]
    assert len(first)==len(last); motion[name]=max((a-b).length for a,b in zip(first,last))
rows=[]
for frame in range(0,61):
    scene.frame_set(int(import_start+frame)); bpy.context.view_layer.update()
    for ob in [resolved['SM_RO_glove.R'],resolved['SM_RO_WristLoft.R']]:
        assert ob.data.shape_keys is not None
        values={k.name:k.value for k in ob.data.shape_keys.key_blocks if k.name!='Basis'}
        rows.append({'imported_frame':int(import_start+frame),'mesh':ob.name,'morph_weights':values})
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':item,'fresh_process':True,'factory_reset_function_called':False,'bone_custom_shape_disabled':True,
 'source_frames':[1,61],'fps':60,'clip_seconds':clip_end-clip_start,'glb_time_range_seconds':[clip_start,clip_end],'imported_action_ranges':action_ranges,'frame_mapping':'source1..61 maps to actual GLB time range and imported action first..last frames; importer preserves time origin',
 'first_check_failure':'TEST_FAILURE: verifier assumed GLB0start; exporter preserves actual frame1 time. Original verifier/log retained; no asset regeneration.',
 'second_check_failure':'TOOL_FAILURE: verifier assumed source-name import object is MESH; glTF imports named container plus actual mesh child. Resolve exact unique descendant and retain mapping; no asset change.',
 'third_check_failure':'TOOL_FAILURE: skin importer reparents mesh outside named node container. Exact GLB node.mesh index to mesh datablock name replaces hierarchy guess; original attempts retained.',
 'source_to_import_mesh_mapping':{n:ob.name for n,ob in resolved.items()},
 'meshes':len(meshes),'bones':len(rigs[0].data.bones),'triangles':report['whole_triangles'],'skins':len(doc.get('skins',[])),
 'animation_count':len(doc['animations']),'animation_channels':sum(len(a['channels']) for a in doc['animations']),
 'embedded_images':len(doc.get('images',[])),'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images if i.source=='FILE'],
 'skeletal_and_morph_playback_samples':samples,'motion_max_vertex_displacement_m':motion,'all61frames_evaluated':True,'morph_readback':rows,
 'prototype_geometry_playback_pass':all(v['pass_0_1mm'] for s in samples for v in s['objects'].values()) and motion['SM_RO_glove.R']>.01 and motion['SM_RO_sword']>.01,
 'verified_scope':'actual local open-to-grip skeletal/morph playback and5samplegeometry; failing source shapes reproduced, not full asset art/animation acceptance',
 'material_sampler_warning':'More than one shader node tex image used for a texture; unresolved, no material equivalence pass',
 'full300frame_skill_combo_accepted':False,'art_accepted':False,'delivered':False}
(QA/'roundtrip.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('RO_WRIST_ROUNDTRIP '+json.dumps({k:v for k,v in result.items() if k not in ['morph_readback','skeletal_and_morph_playback_samples','images']}))
