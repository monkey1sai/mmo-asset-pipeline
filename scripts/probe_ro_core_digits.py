"""Measure separate distal finger branches in the actual welded diagnostic graph."""
from collections import defaultdict
import json
from pathlib import Path
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/qa/ro-swordsman-combo-r005/core-landmark-probe/digits.json'
if OUT.exists(): raise RuntimeError('Preserve digit measurement')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/core-source-comparison/source_comparison.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_Core_Fallback_Source']
bm=bmesh.new(); bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bm.verts.ensure_lookup_table()
report={}
for side,sign in [('R',-1),('L',1)]:
    verts={v for v in bm.verts if sign*v.co.x>.33 and v.co.z<.839}
    groups=[]
    while verts:
        seed=verts.pop(); group=[seed]; stack=[seed]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                other=e.other_vert(v)
                if other in verts: verts.remove(other); group.append(other); stack.append(other)
        if len(group)<5: continue
        lo=[min(v.co[i] for v in group) for i in range(3)]
        hi=[max(v.co[i] for v in group) for i in range(3)]
        tips=[v.co for v in group if v.co.z<lo[2]+.004]
        tips_mean=[sum(v[i] for v in tips)/len(tips) for i in range(3)]
        top=[v.co for v in group if v.co.z>hi[2]-.009]
        top_mean=[sum(v[i] for v in top)/len(top) for i in range(3)]
        groups.append({'count':len(group),'min':lo,'max':hi,'tip':tips_mean,'cut_center':top_mean})
    hand=[v.co for v in bm.verts if sign*v.co.x>.34 and .839<v.co.z<.94]
    outer=sorted(hand,key=lambda p:sign*p.x,reverse=True)[:12]
    report[side]={'distal_groups':sorted(groups,key=lambda g:sign*g['tip'][0]),'outer_thumb_points':[list(p) for p in outer]}
bm.free()
OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
