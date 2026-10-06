"""Classify actual cuff cut rings after v006 refuses multiple boundaries."""
from pathlib import Path
import json,sys
import bpy,bmesh
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r006/v006-cut-diagnosis'; assert not QA.exists(); QA.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r006/v005-thumb-wrist/ro_thumb_contact_checkpoint.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; state=json.loads(rig['state_json']); wrist=Vector(state['rest']['hand.R'][0])
anatomy=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r006/v001-generated-glove/anatomy-and-masks.json').read_text()); rot=Matrix(anatomy['rotation']); sw=Vector(anatomy['source_wrist'])
results=[]
for height in [.036,.040,.046,.052]:
    bm=bmesh.new(); bm.from_mesh(glove.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    point=wrist+rot@(Vector((sw.x,sw.y,height))-sw); normal=rot@Vector((0,0,1))
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=point,plane_no=normal,clear_inner=True,clear_outer=False)
    unseen={e for e in bm.edges if e.is_boundary}; loops=[]
    while unseen:
        seed=unseen.pop(); found={seed}; verts=set(seed.verts); stack=list(verts)
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                if e in unseen:
                    unseen.remove(e); found.add(e)
                    for p in e.verts:
                        if p not in verts: verts.add(p); stack.append(p)
        positions=[rot.inverted()@(v.co-wrist)+sw for v in verts]
        loops.append({'vertices':len(verts),'edges':len(found),'simple':all(sum(e in found for e in v.link_edges)==2 for v in verts),
                      'centroid_native':list(sum(positions,Vector())/len(positions)),'bounds_native':[[min(p[i] for p in positions),max(p[i] for p in positions)] for i in range(3)],
                      'perimeter_m':sum(e.calc_length() for e in found),'points_native':[list(p) for p in positions]})
    results.append({'cut_native_z':height,'loops':loops})
    if height==.046:
        derived=bpy.data.meshes.new('diagnostic-cut'); bm.to_mesh(derived); ob=bpy.data.objects.new('diagnostic-cut',derived); bpy.context.scene.collection.objects.link(ob)
        for mat in glove.data.materials: derived.materials.append(mat)
        for item in bpy.context.scene.objects:
            if item.type=='MESH' and item!=ob: item.hide_render=True
        camera((tuple(point-normal*.18),tuple(point),.20)); bpy.context.scene.render.filepath=str(QA/'cut-ring.png'); bpy.ops.render.render(write_still=True)
    bm.free()
(QA/'cut-loops.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'cut':r['cut_native_z'],'loops':[{k:v for k,v in l.items() if k!='points_native'} for l in r['loops']]} for r in results]))
