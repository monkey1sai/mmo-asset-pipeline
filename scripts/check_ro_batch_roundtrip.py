"""Fresh scene static GLB roundtrip; explicitly not animation acceptance."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import stage, render_views
SOURCE = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-rig-seams/ro_rig_preflight.glb'
EXPECTED = '17c0163cde80e1d6afa38a2dce268f62177b35ca4cbe70bf63fbe26a8b6f7ba8'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-glb-roundtrip'
raw = SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED or QA.exists():
    raise RuntimeError('Preserve source and previous roundtrip')
magic, version, length = struct.unpack_from('<4sII',raw)
chunk_length, chunk_type = struct.unpack_from('<II',raw,12)
if magic != b'glTF' or version != 2 or length != len(raw) or chunk_type != 0x4e4f534a:
    raise RuntimeError('Invalid GLB')
doc = json.loads(raw[20:20+chunk_length])
if any(image.get('uri') for image in doc.get('images',[])):
    raise RuntimeError('External image dependency')
# CLI --factory-startup already supplies a fresh scene. Do not call a preferences
# reset: Blender may perform global extension-package cleanup as a side effect.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE),disable_bone_shape=True)
meshes = [o for o in bpy.data.objects if o.type=='MESH']
rigs = [o for o in bpy.data.objects if o.type=='ARMATURE']
images = [{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images]
triangles = sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
expected_joints = len(doc['skins'][0]['joints'])
if len(meshes) != 8 or len(rigs)!=1 or len(rigs[0].data.bones)!=expected_joints or triangles != 55488:
    raise RuntimeError(f'Fresh import inventory mismatch: meshes={len(meshes)}, rigs={len(rigs)}, bones={[len(r.data.bones) for r in rigs]}, triangles={triangles}, expected_export_joints={expected_joints}')
QA.mkdir(parents=True)
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new('ReviewWorld')
stage()
render_views(QA)
report = {'subject':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},
    'fresh_scene_import':True,'meshes':len(meshes),'bones':len(rigs[0].data.bones),'triangles':triangles,
    'skins':len(doc.get('skins',[])),'skin_joint_counts':[len(s['joints']) for s in doc.get('skins',[])],
    'images':images,'embedded_textures':True,'animation_count':len(doc.get('animations',[])),
    'animation_channels':sum(len(a.get('channels',[])) for a in doc.get('animations',[])),
    'material_count':len(doc.get('materials',[])),
    'bone_custom_shape_disabled':True,
    'prior_inventory_mismatch':'Built-in importer adds an icosphere control display when disable_bone_shape=False; 80 diagnostic triangles are not exported source geometry.',
    'verified_scope':'Static rest geometry, skin/joint inventory and material image presence. Actual five views retained.',
    'animation_acceptance':False,'art_acceptance':False,'no_full_motion_roundtrip_performed':True}
(QA / 'roundtrip.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_STATIC_ROUNDTRIP '+json.dumps(report))
