"""Measure changed-corner source UV islands and retain texture-view evidence."""
from pathlib import Path
import json,hashlib
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r007/v003-thumb-patch'
report=json.loads((QA/'patch.json').read_text());source=ROOT/report['source']['path']
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
me=bpy.data.objects['SM_RO_RightHand_Exterior'].data;me.calc_loop_triangles()
bm=bmesh.new();bm.from_mesh(me);bm.faces.index_update();uv=bm.loops.layers.uv.active
groups={};todo=[];island=0
for seed in bm.faces:
    if seed.index in groups:continue
    todo=[seed]
    while todo:
        f=todo.pop()
        if f.index in groups:continue
        groups[f.index]=island
        for edge in f.edges:
            for other in edge.link_faces:
                if other==f or other.index in groups:continue
                a={l.vert: l[uv].uv for l in f.loops if l.vert in edge.verts}
                b={l.vert: l[uv].uv for l in other.loops if l.vert in edge.verts}
                if all((a[v]-b[v]).length<1e-6 for v in edge.verts):todo.append(other)
    island+=1
mixed=[];per_face=[]
for row in report['UV_transfer']:
    islands=[groups[me.loop_triangles[i].polygon_index] for i in row['nearest_original_triangle_per_corner']]
    per_face.append({'face':row['face'],'source_UV_islands':islands})
    if len(set(islands))>1:mixed.append(per_face[-1])
bm.free()
result={'source':report['source'],'subject':report['artifact'],'source_UV_island_count':island,
    'changed_faces':len(per_face),'mixed_source_island_faces':mixed,'per_face':per_face,
    'cross_island_interpolation_gate':not mixed,'actual_texture_views_inspected':['front-texture.png','back-texture.png'],
    'visual_judgment':'Brown glove seams readable in front/back at actual render; no obvious large stretched color region seen',
    'limitations':['Same source island does not prove absence of seam-path interpolation or texture distortion','Tangent normal equivalence not established; functional test before any final rebake']}
with (QA/'UV-islands.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print('RO_PATCH_UV '+json.dumps({'islands':island,'mixed_changed_faces':len(mixed)}))
