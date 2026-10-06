"""Independently read back fin repair and assert every retained face's positions and UV."""
from collections import Counter
import json
from pathlib import Path
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-fit/topology-readback.json'
if OUT.exists(): raise RuntimeError('Preserve verification')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/core-source-comparison/source_comparison.blend'),load_ui=False,use_scripts=False)
src=bpy.data.objects['SM_RO_Core_Fallback_Source']
bm=bmesh.new(); bm.from_mesh(src.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bm.faces.ensure_lookup_table(); bm.faces.index_update()
uv=bm.loops.layers.uv.active
def key(face):
    return tuple(sorted(tuple(round(c,7) for c in loop.vert.co)+tuple(round(c,7) for c in loop[uv].uv) for loop in face.loops))
fins=[f for f in bm.faces if len(f.verts)==3 and all(v.co.z>1.46 for v in f.verts) and sorted(len(e.link_faces) for e in f.edges)==[1,1,3]]
assert len(fins)==4
saved=[]
for f in fins:
    shared=next(e for e in f.edges if len(e.link_faces)==3)
    saved.append({'face_id_in_this_weld':f.index,'position_uv_pairs':[list(x) for x in key(f)],'adjacent_shell_face_ids':[other.index for other in shared.link_faces if other!=f]})
expected=Counter(key(f) for f in bm.faces if f not in fins)
bm.free()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/v002-fit/ro_core_fit.blend'),load_ui=False,use_scripts=False)
core=bpy.data.objects['SM_RO_core']
bm=bmesh.new(); bm.from_mesh(core.data); uv=bm.loops.layers.uv.active
actual=Counter(key(f) for f in bm.faces)
assert actual==expected,'Retained geometry/UV loops changed'
nonmanifold=sum(not e.is_manifold for e in bm.edges)
assert nonmanifold==0
report={'fin_faces':saved,'removed_triangles':4,'remaining_face_position_uv_multisets_exact_to_1e_7':True,'nonmanifold_edges':nonmanifold,'core_triangles':sum(len(f.verts)-2 for f in bm.faces),'source_body_digits_and_retained_face_geometry_changed':False,'accepted_scope':'local topology and UV readback only; anatomy/rig/animation unaccepted'}
bm.free()
OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('CORE_TOPOLOGY_READBACK '+json.dumps({k:v for k,v in report.items() if k!='fin_faces'}))
