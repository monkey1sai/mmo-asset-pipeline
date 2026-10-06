"""True-surface and stretch diagnosis for local prototype; does not accept the asset."""
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import pose
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-roll/deformation.json'
if QA.exists(): raise RuntimeError('Preserve deformation diagnostics')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-roll/ro_roll_checked.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']; state=json.loads(rig['state_json'])
pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),two_hands=False)
deps=bpy.context.evaluated_depsgraph_get(); co=core.evaluated_get(deps); so=sword.evaluated_get(deps)
stretch=[]
for e in core.data.edges:
    a,b=(core.data.vertices[i] for i in e.vertices)
    if not (a.co.x<-.34 and b.co.x<-.34 and max(a.co.z,b.co.z)<1.03): continue
    native=(a.co-b.co).length; posed=(co.data.vertices[a.index].co-co.data.vertices[b.index].co).length
    if native<1e-8: continue
    row={'vertices':list(e.vertices),'source':[list(a.co),list(b.co)],'stretch_ratio':posed/native,'weights':[{core.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8} for v in (a,b)]}
    stretch.append(row)
bm=bmesh.new(); bm.from_mesh(sword.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
nonmanifold=sum(not e.is_manifold for e in bm.edges); bm.free()
pts=[so.matrix_world@v.co for v in so.data.vertices]; solid=BVHTree.FromPolygons(pts,[list(f.vertices) for f in so.data.polygons])
center=rig.pose.bones['sword'].head; axis=(rig.pose.bones['sword'].tail-center).normalized()
faces=[list(f.vertices) for f in so.data.polygons if all(-.112<(pts[i]-center).dot(axis)<.085 for i in f.vertices)]
handle=BVHTree.FromPolygons(pts,faces)
directions=[Vector((.713,.389,.587)).normalized(),Vector((.419,.831,.365)).normalized()]
def inside(p,direction):
    origin=p+direction*1e-6; count=0
    for _ in range(80):
        hit,normal,index,dist=solid.ray_cast(origin,direction,4)
        if hit is None: return bool(count%2)
        count+=1; origin=hit+direction*1e-6
    return None
parts={}; disagreements=0
for part,indices in state['contact_pad_vertices']['R'].items():
    distances=[]; penetrating=[]
    for i in indices:
        p=co.matrix_world@co.data.vertices[i].co; hit,normal,f,d=handle.find_nearest(p); distances.append(d)
        votes=[inside(p,ray) for ray in directions]
        if len(set(votes))>1: disagreements+=1
        _,_,_,depth=solid.find_nearest(p)
        if all(votes) and depth>.001: penetrating.append({'vertex':i,'depth_m':depth})
    parts[part]={'fixed_pad_vertex_count':len(indices),'minimum_pad_distance_m':min(distances),'pad_mean_distance_m':sum(distances)/len(distances),'vertices_inside_deeper_than1mm':len(penetrating),'maximum_penetration_m':max((r['depth_m'] for r in penetrating),default=0)}
# Triangle centroid and edge-midpoint interior checks supplement, not replace triangle intersection.
interior_samples=[]; inspected=0
for f in co.data.polygons:
    if not all(core.data.vertices[i].co.x<-.34 and core.data.vertices[i].co.z<.923 for i in f.vertices): continue
    vs=[co.matrix_world@co.data.vertices[i].co for i in f.vertices]
    samples=[sum(vs,Vector())/len(vs)]+[a.lerp(b,.5) for a,b in zip(vs,vs[1:]+vs[:1])]
    for p in samples:
        inspected+=1; votes=[inside(p,r) for r in directions]
        if len(set(votes))>1: disagreements+=1
        _,_,_,depth=solid.find_nearest(p)
        if all(votes) and depth>.001: interior_samples.append(depth)
report={'sword_welded_nonmanifold':nonmanifold,'inside_method':'Two odd/even rays against complete actual sword; disagreement retained, no closedness inference if nonmanifold>0.',
    'fixed_pad_vertices':parts,'ray_disagreements':disagreements,'face_and_edge_samples':inspected,'samples_inside_deeper_than1mm':len(interior_samples),'maximum_sample_penetration_m':max(interior_samples,default=0),
    'most_stretched_local_edges':sorted(stretch,key=lambda r:-r['stretch_ratio'])[:20],'most_compressed_local_edges':sorted(stretch,key=lambda r:r['stretch_ratio'])[:12],
    'surface_and_deformation_accepted':False,'threshold_is_diagnostic':True}
QA.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print('RO_HAND_SURFACE '+json.dumps({k:v for k,v in report.items() if not k.startswith('most_')}))
