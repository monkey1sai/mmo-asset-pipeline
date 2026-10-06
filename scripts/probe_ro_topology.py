"""Check geometry connectivity after welding only duplicated GLB seam vertices."""
from pathlib import Path
import json
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bm=bmesh.new(); bm.from_mesh(ob.data)
before=len(bm.verts)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
remaining=set(bm.verts); components=[]
while remaining:
    stack=[remaining.pop()]; group=[]
    while stack:
        v=stack.pop();group.append(v)
        for e in v.link_edges:
            n=e.other_vert(v)
            if n in remaining:remaining.remove(n);stack.append(n)
    pts=[ob.matrix_world @ v.co for v in group]
    components.append({'vertices':len(group),'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)]})
report={'source_sha256':'9350ee0a6cbe9af02bedabcc7ccee01153b7af90edc7f604dae67d205999e4c1','method':'Weld exact GLB duplication at 1e-6m in scratch scene; UV loops retained; source unchanged','before':before,'after':len(bm.verts),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'boundary':sum(e.is_boundary for e in bm.edges),'components':sorted(components,key=lambda x:-x['vertices'])}
(ROOT/'runs/qa/ro-swordsman-combo/rodin-v001-static/weld-topology.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report));bm.free()
