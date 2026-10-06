"""Fresh import of the static rig preflight, explicitly expecting no animation."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import stage,render_views
source=ROOT/'assets/processed/ro-swordsman-combo-r003/v001/ro_swordsman_preflight_final.glb'
qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001';raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
magic,version,total=struct.unpack_from('<4sII',raw);assert magic==b'glTF' and version==2 and total==len(raw)
length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a;doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
external=[i['uri'] for category in ['images','buffers'] for i in doc.get(category,[]) if i.get('uri') and not i['uri'].startswith('data:')];assert not external
assert len(doc.get('skins',[]))==1 and len(doc['skins'][0]['joints'])==46 and not doc.get('animations')
formats={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)};widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(i):
    ac=doc['accessors'][i];view=doc['bufferViews'][ac['bufferView']];fmt,size=formats[ac['componentType']];width=widths[ac['type']]
    stride=view.get('byteStride',size*width);start=view.get('byteOffset',0)+ac.get('byteOffset',0)
    assert start+(ac['count']-1)*stride+size*width<=view.get('byteOffset',0)+view['byteLength']<=len(binary)
    values=[struct.unpack_from('<'+fmt*width,binary,start+j*stride) for j in range(ac['count'])]
    assert all(math.isfinite(x) for row in values for x in row);return values
triangles=0;vertices=0
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        attrs=primitive['attributes'];positions=accessor(attrs['POSITION']);indices=accessor(primitive['indices']);triangles+=len(indices)//3;vertices+=len(positions)
        assert all(i[0]<len(positions) for i in indices)
        weights=accessor(attrs['WEIGHTS_0']);joints=accessor(attrs['JOINTS_0']);assert len(weights)==len(joints)==len(positions)
        assert all(abs(sum(ws)-1)<1e-4 and min(ws)>=0 for ws in weights)
        assert all(max(js)<46 for js in joints)
assert triangles==39946 and triangles<=60000
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE');widgets={pb.custom_shape for pb in rig.pose.bones if pb.custom_shape}
meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob not in widgets];assert len(meshes)==5
body=max(meshes,key=lambda ob:len(ob.data.vertices));eo=body.evaluated_get(bpy.context.evaluated_depsgraph_get());data=eo.to_mesh();points=[eo.matrix_world@v.co for v in data.vertices]
lo=[min(p[i] for p in points) for i in range(3)];hi=[max(p[i] for p in points) for i in range(3)];eo.to_mesh_clear()
report={'subject':source.relative_to(ROOT).as_posix(),'subject_sha256':sha,'fresh_import':True,'tool':bpy.app.version_string,'bones':len(rig.data.bones),
        'skin_count':len(doc['skins']),'mesh_count':len(meshes),'triangles':triangles,'vertices':vertices,'normalized_finite_skin_weights':True,
        'external_dependencies':external,'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE'],
        'actual_body_bounds_m':{'min':lo,'max':hi},'animation_count':0,'continuous_animation_check':'fail_missing_requested_animation',
        'limits':'Static rig/embedded texture inventory and fresh import only; no full deformation, contact, art or delivery acceptance.'}
stage();render_views(qa/'preflight-roundtrip-views');assert sha==hashlib.sha256(source.read_bytes()).hexdigest()
target=qa/'preflight-fresh-import.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
