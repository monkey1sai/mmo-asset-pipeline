"""Read-only rest/posed edge and region diagnosis; does not save a master."""
import ast
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'assets/processed/ro-swordsman-combo-r003/v001/ro_swordsman_hands_restored.blend'
sha=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
scene=bpy.context.scene;body=bpy.data.objects['SM_RO_SourcePreservedBody'];rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones}
PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pose functions>','exec'),globals())
pose(1,.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75))
ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();edges=[]
for edge in body.data.edges:
    i,j=edge.vertices;old=(body.data.vertices[i].co-body.data.vertices[j].co).length;new=(mesh.vertices[i].co-mesh.vertices[j].co).length
    if old>1e-6 and new>.1 and new/old>8:
        edges.append({'edge':edge.index,'ratio':new/old,'length_m':new,'endpoints':[{'index':k,'rest':list(body.data.vertices[k].co),'posed':list(mesh.vertices[k].co),
                      'weights':{body.vertex_groups[g.group].name:g.weight for g in body.data.vertices[k].groups if g.weight>1e-8}} for k in [i,j]]})
ob.to_mesh_clear()
report={'subject_sha256':sha,'diagnostic_not_acceptance':True,'pose':'deep-crouch','count':len(edges),'edges':sorted(edges,key=lambda e:-e['ratio'])[:30]}
assert sha==hashlib.sha256(path.read_bytes()).hexdigest()
target=ROOT/'runs/qa/ro-swordsman-combo-r003/v001/cloth-boundary-diagnosis.json'
assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({**report,'edges':report['edges'][:5]}))
