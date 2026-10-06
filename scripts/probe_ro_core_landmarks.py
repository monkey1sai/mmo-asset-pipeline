"""Read actual new core sections/topology and render diagnostic hands; no source edit."""
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/core-landmark-probe'
if QA.exists():
    raise RuntimeError('Preserve prior diagnostics')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/core-source-comparison/source_comparison.blend'),load_ui=False,use_scripts=False)
core=bpy.data.objects['SM_RO_Core_Fallback_Source']
old=bpy.data.objects['SM_RO_Core_Batch_Source']
core.hide_render=False; old.hide_render=True
QA.mkdir(parents=True)
bm=bmesh.new(); bm.from_mesh(core.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
bad=[{'edge':e.index,'face_count':len(e.link_faces),'ends':[list(v.co) for v in e.verts]} for e in bm.edges if not e.is_manifold]
section=[]
for z in [.06,.10,.20,.32,.45,.55,.65,.75,.85,.9,.95,1.0,1.05,1.1,1.15,1.2,1.25,1.3,1.35,1.4,1.45]:
    points=[v.co for v in core.data.vertices if abs(v.co.z-z)<.009]
    right=[p for p in points if p.x>.27]
    center=[p for p in points if abs(p.x)<.25]
    row={'z':z,'count':len(points)}
    for label,pts in [('arm_or_hand',right),('center',center)]:
        if pts: row[label]={'count':len(pts),'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
    section.append(row)
bm.free()
for side,sign in [('R',-1),('L',1)]:
    target=Vector((sign*.447,-.012,.88))
    for name,offset in [('front',(0,-2,0)),('back',(0,2,0)),('three-quarter',(sign*.8,-2,.15))]:
        camera((tuple(target+Vector(offset)),tuple(target),.32))
        bpy.context.scene.render.filepath=str(QA/f'hand-{side}-{name}.png')
        bpy.ops.render.render(write_still=True)
report={'method':'actual normalized new core vertices; position-weld diagnostics only','nonmanifold_edges':bad,'sections':section,'source_geometry_modified':False,'rig_accepted':False}
(QA/'probe.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('CORE_LANDMARK_PROBE '+json.dumps({'bad_edges':bad,'sections':section}))
