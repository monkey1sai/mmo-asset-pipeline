"""Independent fresh GLB import and finite geometry checks; no art acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import stage, render_views
p=argparse.ArgumentParser(); p.add_argument('--version',required=True)
p.add_argument('--phase', choices=['ro-swordsman-combo-r002','ro-swordsman-combo-r003'], default='ro-swordsman-combo-r002')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.version not in {'baseline','v001','v002','v003'}: raise ValueError('Invalid phase version')
out=ROOT/'assets/processed'/a.phase/a.version
qa=ROOT/'runs/qa'/a.phase/a.version
source=out/('ro_source_baseline.glb' if a.version=='baseline' else 'ro_swordsman_combo.glb'); raw=source.read_bytes()
magic,version,total=struct.unpack_from('<4sII',raw,0); assert magic==b'glTF' and version==2 and total==len(raw)
length,kind=struct.unpack_from('<II',raw,12); assert kind==0x4e4f534a
doc=json.loads(raw[20:20+length]); external=[i.get('uri') for i in doc.get('images',[]) if 'uri' in i]
assert not external
binary=raw[28+length:]
formats={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)};widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(index):
    ac=doc['accessors'][index];bv=doc['bufferViews'][ac['bufferView']];fmt,size=formats[ac['componentType']];width=widths[ac['type']]
    stride=bv.get('byteStride',size*width);start=bv.get('byteOffset',0)+ac.get('byteOffset',0)
    values=[struct.unpack_from('<'+fmt*width,binary,start+j*stride) for j in range(ac['count'])]
    assert all(math.isfinite(x) for row in values for x in row);return values
triangles=0;weight_errors=[];times=[]
for mesh in doc.get('meshes',[]):
    for pr in mesh['primitives']:
        vertices=accessor(pr['attributes']['POSITION']);triangles+=len(accessor(pr['indices']))//3
        if a.version!='baseline':
            attrs=pr['attributes'];assert 'JOINTS_0' in attrs and 'WEIGHTS_0' in attrs
            weights=accessor(attrs['WEIGHTS_0']);joints=accessor(attrs['JOINTS_0'])
            assert len(weights)==len(joints)==len(vertices)
            for ws,js in zip(weights,joints):
                if abs(sum(ws)-1)>1e-4 or min(ws)<0 or max(js)>=len(doc['skins'][0]['joints']):weight_errors.append(mesh['name'])
for animation in doc.get('animations',[]):
    for sampler in animation['samplers']:
        samples=[r[0] for r in accessor(sampler['input'])];assert all(x<y for x,y in zip(samples,samples[1:]));times.extend(samples);accessor(sampler['output'])
if a.version!='baseline':
    assert len(doc.get('skins',[]))==1
    assert len(doc['skins'][0]['joints'])==25 if a.phase=='ro-swordsman-combo-r002' else len(doc['skins'][0]['joints'])>=25
    assert not weight_errors and triangles<=60000
    assert len(doc['animations'])==1 and min(times)==0 and abs(max(times)-299/60)<1e-5
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps=60; bpy.ops.import_scene.gltf(filepath=str(source))
rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
widgets={pb.custom_shape for r in rigs for pb in r.pose.bones if pb.custom_shape}
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in widgets]
allpoints=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
lo=[min(v[i] for v in allpoints) for i in range(3)]; hi=[max(v[i] for v in allpoints) for i in range(3)]
report={'subject':source.relative_to(ROOT).as_posix(),'subject_sha256':hashlib.sha256(raw).hexdigest(),'tool':bpy.app.version_string,'fresh_import':True,'mesh_count':len(meshes),'bones':sum(len(r.data.bones) for r in rigs),'animations':[x.get('name') for x in doc.get('animations',[])],'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE'],'external_dependencies':external,'bind_bounds_blender_m':{'min':lo,'max':hi},'skin_count':len(doc.get('skins',[])),'triangles':triangles,'weight_errors':weight_errors,'sample_seconds':[min(times),max(times)] if times else [],'fresh_frame_mapping':'GLB0..299 = original Blender1..300 at60fps','visual_acceptance':'requires reviewer; render views alone is not pass'}
stage(); render_views(qa/'roundtrip-views',frame=0 if a.version!='baseline' else 1)
(qa/'fresh-import.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('FRESH_IMPORT '+json.dumps(report))
