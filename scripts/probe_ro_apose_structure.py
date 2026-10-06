"""Read-only local topology diagnosis of the metric baseline; never save master."""
import hashlib
import json
from pathlib import Path
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'assets/processed/ro-swordsman-combo-r003/baseline/ro_source_baseline.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob=bpy.data.objects['SM_RO_APoseSource_0']
bm=bmesh.new(); bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
edges=[{'vertices':[list(v.co) for v in e.verts], 'linked_faces':len(e.link_faces), 'length_m':e.calc_length(),
        'kind':'boundary' if e.is_boundary else 'wire' if e.is_wire else 'multiple_faces'} for e in bm.edges if not e.is_manifold]
sections={}
for label,(low,high,minimum_x) in {'shoulder':(1.27,1.34,.18),'elbow':(1.055,1.12,.24),'wrist':(.87,.93,.34),'palm':(.79,.87,.36),'fingertips':(.72,.79,.37),'hip':(.81,.91,0),'knees':(.43,.49,0),'ankles':(.085,.15,0)}.items():
    points=[v.co for v in bm.verts if low<=v.co.z<=high and v.co.x>=minimum_x]
    sections[label]={'vertices':len(points),'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
report={'baseline_sha256':before, 'tolerance_m':1e-6, 'nonmanifold_edges':edges,'sections_positive_x':sections, 'observation':'Read-only diagnosis, not repair or rig acceptance.'}
bm.free()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(ROOT/'runs/qa/ro-swordsman-combo-r003/baseline/structure-diagnosis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
