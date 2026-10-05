"""Read an actual GLB and roundtrip it through a fresh Blender scene.

Numerical checks are deliberately separate from visual/action acceptance.
No construction helper is imported by this independent inspection script.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--version',choices=['v001','v002','v003','v004'],required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=ROOT/'assets/processed/ro-swordsman-combo'/a.version/'ro_swordsman_combo.glb'
qa=ROOT/'runs/qa/ro-swordsman-combo'/a.version
raw=source.read_bytes()
magic,version,total=struct.unpack_from('<4sII',raw,0)
assert magic==b'glTF' and version==2 and total==len(raw)
offset=12; chunks={}
while offset<len(raw):
    length,kind=struct.unpack_from('<II',raw,offset)
    assert offset+8+length<=len(raw)
    chunks[kind]=raw[offset+8:offset+8+length]
    offset+=8+length
doc=json.loads(chunks[0x4E4F534A]); binary=chunks[0x004E4942]
formats={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}
widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(i):
    ac=doc['accessors'][i]; bv=doc['bufferViews'][ac['bufferView']]
    fmt,size=formats[ac['componentType']]; width=widths[ac['type']]
    stride=bv.get('byteStride',size*width)
    start=bv.get('byteOffset',0)+ac.get('byteOffset',0)
    assert start+(ac['count']-1)*stride+size*width<=bv.get('byteOffset',0)+bv['byteLength']<=len(binary)
    values=[struct.unpack_from('<'+fmt*width,binary,start+j*stride) for j in range(ac['count'])]
    assert all(math.isfinite(v) for row in values for v in row)
    return values
assert len(doc.get('skins',[]))==1
joints=doc['skins'][0]['joints']; assert len(joints)>=25
errors=[]; weighted=0; vertices=0; triangles=0; animated_joints=set(); times=[]
for me in doc['meshes']:
    for pr in me['primitives']:
        attrs=pr['attributes']; pos=accessor(attrs['POSITION']); vertices+=len(pos)
        if 'JOINTS_0' not in attrs or 'WEIGHTS_0' not in attrs:
            errors.append('mesh without skin attributes: '+me.get('name','')); continue
        js=accessor(attrs['JOINTS_0']); ws=accessor(attrs['WEIGHTS_0'])
        assert len(js)==len(ws)==len(pos)
        for joint,weight in zip(js,ws):
            if any(j>=len(joints) for j in joint): errors.append('joint out of range')
            if abs(sum(weight)-1)>1e-4 or min(weight)<0: errors.append('invalid normalized weight')
        weighted+=len(pos)
        indices=accessor(pr['indices']); triangles+=len(indices)//3
        assert all(idx[0]<len(pos) for idx in indices)
for animation in doc.get('animations',[]):
    for channel in animation['channels']:
        if channel['target']['node'] in joints: animated_joints.add(channel['target']['node'])
        sampler=animation['samplers'][channel['sampler']]
        t=[row[0] for row in accessor(sampler['input'])]
        assert all(x<y for x,y in zip(t,t[1:])); times.extend(t)
        accessor(sampler['output'])
assert times and min(times)==0 and abs(max(times)-299/60)<1e-5
assert len(animated_joints)>=20

# Fresh import; do not execute the editable master or share the construction scene.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps=60
before_import=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(source))
rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
assert len(rigs)==1
rig=rigs[0]
widgets={pb.custom_shape for pb in rig.pose.bones if pb.custom_shape}
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in widgets]
bindings={ob.name:{'parent':ob.parent.name if ob.parent else None,'parent_type':ob.parent_type,'parent_bone':ob.parent_bone,'armature_modifiers':[mod.object.name for mod in ob.modifiers if mod.type=='ARMATURE' and mod.object]} for ob in meshes}
unbound=[ob.name for ob in meshes if not (any(mod.type=='ARMATURE' and mod.object==rig for mod in ob.modifiers) or (ob.parent==rig and ob.parent_type=='BONE' and ob.parent_bone in rig.pose.bones))]
assert not unbound,unbound
poses={}; corners={}; hand_positions={}
frames=[1,13,25,38,50,63,75,88,100,110,120,133,145,158,170,183,195,208,220,238,255,268,280,300]
for f in frames:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    poses[str(f)]={n:list(rig.pose.bones[n].matrix.translation) for n in ['head','hand.L','hand.R','foot.L','foot.R','sword']}
    deps=bpy.context.evaluated_depsgraph_get()
    coords=[]
    for ob in meshes:
        eo=ob.evaluated_get(deps); data=eo.to_mesh()
        coords.extend([eo.matrix_world@v.co for v in data.vertices]); eo.to_mesh_clear()
    corners[str(f)]={'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]}
motion=sum(sum((poses[str(f)]['hand.R'][i]-poses['1']['hand.R'][i])**2 for i in range(3)) for f in frames[1:])
assert motion>.01
construction=json.loads((qa/'construction-check.json').read_text(encoding='utf-8'))
weld=[x for x in construction.get('weld',[]) if x['merged']]
report={'subject':source.relative_to(ROOT).as_posix(),'subject_sha256':hashlib.sha256(raw).hexdigest(),
        'file_size_bytes':len(raw),'format':'GLB2','skin_count':len(doc['skins']),'joints':len(joints),
        'vertices_exported':vertices,'weighted_vertices':weighted,'triangles':triangles,
        'animations':[x.get('name') for x in doc['animations']], 'animated_joint_count':len(animated_joints),
        'time_seconds':[min(times),max(times)],'playback_fps':60,'sampled_frames':frames,
        'fresh_import_rig_count':len(rigs),'fresh_import_mesh_count':len(meshes),
        'imported_bindings':bindings,
        'importer_bone_widgets_excluded':[ob.name for ob in widgets],
        'pose_samples':poses,'evaluated_bounds':corners,'hand_motion_squared_sum':motion,
        'weld_changes':weld,'numeric_errors':errors,'numeric_roundtrip':'pass' if not errors else 'fail',
        'visual_roundtrip':'not_run','deformation_acceptance':'not_run','continuous_action_acceptance':'not_run',
        'note':'Skin/channels, normalized weights, finite positions and imported motion are verified. These do not establish likeness, continuous skin topology, grip, contacts, collisions or artistic quality.'}
(qa/'roundtrip-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not errors,errors
print('RO_NUMERIC_ROUNDTRIP '+a.version+' pass; '+str(triangles)+' triangles; '+str(len(animated_joints))+' animated joints')
