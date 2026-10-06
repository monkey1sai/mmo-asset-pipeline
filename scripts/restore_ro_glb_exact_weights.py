"""Restore frozen original weights after Blender's hardcoded export cutoff."""
from pathlib import Path
from datetime import datetime,timezone
import struct,json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r010'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
record=read(QA/'v004-certified-animation/combined-export.json');source=ROOT/record['artifact']['path'];assert artifact(source)==record['artifact']
original=source.read_bytes();blob=bytearray(original);n=struct.unpack_from('<I',blob,12)[0];doc=json.loads(blob[20:20+n].decode('utf-8'))
binary_start=28+n;assert struct.unpack_from('<I',blob,24+n)[0]==0x004e4942
primitive=next(p for m in doc['meshes'] for p in m['primitives'] if '_R010_ID' in p['attributes']);attrs=primitive['attributes']
dtypes={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}
def accessor(name,width):
    a=doc['accessors'][attrs[name]];assert 'sparse' not in a
    v=doc['bufferViews'][a['bufferView']];dt=np.dtype(dtypes[a['componentType']]);offset=binary_start+v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',dt.itemsize*width)
    assert offset+(a['count']-1)*stride+dt.itemsize*width<=len(blob)
    return np.ndarray((a['count'],width),dtype=dt,buffer=blob,offset=offset,strides=(stride,dt.itemsize)),offset,stride
idarray,_,_=accessor('_R010_ID',1);ids=[round(float(i)) for i in idarray[:,0]]
assert set(ids)==set(range(904))
weights,wo,ws=accessor('WEIGHTS_0',4);joints,jo,js=accessor('JOINTS_0',4)
assert weights.dtype==np.dtype('<f4') and len(weights)==len(ids)==len(joints)
joint_names=[doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']];lookup={n:i for i,n in enumerate(joint_names)}
snapshot=ROOT/'runs/qa/ro-swordsman-combo-r010/baseline/mesh-and-weights.json'
source_weights=read(snapshot)['weights'];before=[];affected=set();allowed=set()
for row,i in enumerate(ids):
    old={joint_names[int(joints[row,k])]:float(weights[row,k]) for k in range(4) if weights[row,k]>0}
    target=source_weights[str(i)];assert 1<=len(target)<=4 and all(n in lookup for n in target)
    assert abs(sum(target.values())-1)<1e-6
    ordered=sorted(target.items(),key=lambda x:-x[1]);error=sum(abs(old.get(n,0)-target.get(n,0)) for n in set(old)|set(target))
    if error>1e-7:affected.add(i);before.append({'source_id':i,'prior_export_weights':old,'frozen_weights':target,'prior_L1_difference':error})
    weights[row]=0;joints[row]=0
    for k,(name,value) in enumerate(ordered):weights[row,k]=value;joints[row,k]=lookup[name]
    for offset,stride,array in [(wo,ws,weights),(jo,js,joints)]:allowed.update(range(offset+row*stride,offset+row*stride+array.dtype.itemsize*4))
    restored={joint_names[int(joints[row,k])]:float(weights[row,k]) for k in range(4) if weights[row,k]>0}
    assert restored==target,(i,restored,target)
diff=[i for i,(a,b) in enumerate(zip(original,blob)) if a!=b];assert set(diff)<=allowed and len(blob)==len(original)
dest=source.with_name('right_hand_grasp_61f_exact_weights.glb')
with dest.open('xb') as f:f.write(blob)
save(QA/'v004-certified-animation/exact-weights-export.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'artifact':artifact(dest),'source_blend':record['source_blend'],
 'prior_export':record['artifact'],'frozen_weights':artifact(snapshot),'sourceID_attribute':'_R010_ID','source_ids':904,
 'affected_original_weight_ids':len(affected),'affected_ids':sorted(affected),'lost_weight_examples':before[:20],
 'changed_bytes':len(diff),'permitted_change':'Only selected original-ID hand JOINTS_0 and WEIGHTS_0 payload bytes; all other GLB bytes exactunchanged.',
 'all_other_bytes_unchanged':True,'geometry_UV_morph_bones_animations_unchanged':True,'protected_thumb_original_weights_restored':True,
 'weights_match_frozen_float32_exact':True,'no_source_or_global_addon_change':True,'new_candidate_or_clock_reset':False,
 'root_cause':'Blender4.5official exporter primitive_extract.py __get_bone_data hardcodedmin_influence0.0001; rawexport artifacts and failed1umcheck preserved.',
 'fresh_GLb':'pending'})
print(json.dumps({'exact_weights':str(dest),'affected_ids':len(affected),'changed_bytes':len(diff),'all_other_bytes_unchanged':True}))
