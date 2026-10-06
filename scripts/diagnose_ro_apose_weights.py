"""Read-only identify cross-region skin weights causing actual stress artifacts."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'assets/processed/ro-swordsman-combo-r003/v001/ro_swordsman_refined_preflight.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
body=bpy.data.objects['SM_RO_SourcePreservedBody'];bpy.context.scene.frame_set(1)
eo=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=eo.to_mesh()
rows=[];leaks=[]
for v,target in zip(body.data.vertices,mesh.vertices):
    groups=[{'bone':body.vertex_groups[g.group].name,'weight':g.weight} for g in v.groups if g.weight>1e-5]
    moved=(target.co-v.co).length
    finger=sum(x['weight'] for x in groups if x['bone'].startswith(('finger','thumb','hand')))
    if moved>.30 or (abs(v.co.x)<.30 and .80<v.co.z<1.10 and finger>.05):
        rows.append({'index':v.index,'source':list(v.co),'posed':list(target.co),'distance_m':moved,'groups':groups})
    if abs(v.co.x)<.30 and .80<v.co.z<1.10 and finger>.05:leaks.append(v.index)
stretched=[]
for edge in body.data.edges:
    i,j=edge.vertices
    old=(body.data.vertices[i].co-body.data.vertices[j].co).length
    length=(mesh.vertices[i].co-mesh.vertices[j].co).length
    if old>1e-6 and length>.1 and length/old>8:
        stretched.append({'edge':edge.index,'source_length_m':old,'posed_length_m':length,'stretch_ratio':length/old,
                          'endpoints':[{'index':k,'source':list(body.data.vertices[k].co),'posed':list(mesh.vertices[k].co),
                                        'groups':[{'bone':body.vertex_groups[g.group].name,'weight':g.weight} for g in body.data.vertices[k].groups if g.weight>1e-5]} for k in [i,j]]})
eo.to_mesh_clear()
report={'subject_sha256':before,'frame':1,'waist_with_hand_finger_weight_over5pct':len(leaks),'largest_movements':sorted(rows,key=lambda x:-x['distance_m'])[:25],
        'edges_stretched_over8x':len(stretched),'largest_stretches':sorted(stretched,key=lambda x:-x['stretch_ratio'])[:10],
        'method':'Actual evaluated source/posed vertex pairing and named weights, no master save or manual inferred classification.'}
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(ROOT/'runs/qa/ro-swordsman-combo-r003/v001/weight-stretch-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='largest_movements'}))
