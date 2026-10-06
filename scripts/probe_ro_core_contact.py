"""Read back true evaluated finger/palm vertices against generated sword surface."""
from collections import defaultdict
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import pose
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-contact-probe'
if QA.exists(): raise RuntimeError('Preserve actual contact diagnostics')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/v002-rig-minimal/ro_core_rig.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json'])
core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']
pose(rig,state,.89,(-.08,-.24,1.12),(0,-.1,.995),two_hands=False)
deps=bpy.context.evaluated_depsgraph_get()
co=core.evaluated_get(deps); so=sword.evaluated_get(deps)
points=[so.matrix_world@v.co for v in so.data.vertices]
axis=(rig.pose.bones['sword'].tail-rig.pose.bones['sword'].head).normalized(); center=rig.pose.bones['sword'].head
faces=[list(f.vertices) for f in so.data.polygons if all(-.112<(points[i]-center).dot(axis)<.085 for i in f.vertices)]
if len(faces)<8: raise RuntimeError('Insufficient actual handle face sample')
tree=BVHTree.FromPolygons(points,faces); whole=BVHTree.FromPolygons(points,[list(f.vertices) for f in so.data.polygons])
direction=Vector((.713,.389,.587)).normalized()
def inside(p):
    origin=p+direction*1e-6; count=0
    for _ in range(40):
        hit,normal,index,dist=whole.ray_cast(origin,direction,3)
        if hit is None: return bool(count%2)
        count+=1; origin=hit+direction*1e-6
    raise RuntimeError('Ambiguous interior ray')
groups=defaultdict(list)
for v in core.data.vertices:
    if not(v.co.x<-.34 and v.co.z<.96): continue
    weights={core.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}
    name=max(weights,key=weights.get)
    if name=='hand.R': part='palm'
    elif name.startswith('finger') and '.R_' in name: part=name.split('.')[0]
    elif name.startswith('thumb.R'): part='thumb'
    else: continue
    p=co.matrix_world@co.data.vertices[v.index].co
    hit,normal,index,dist=tree.find_nearest(p)
    if hit is None: continue
    interior=inside(p)
    _,_,_,solid_distance=whole.find_nearest(p)
    groups[part].append({'vertex':v.index,'source':list(v.co),'posed':list(p),'handle_distance_m':dist,'inside_weapon':interior,'depth_if_inside_m':solid_distance if interior else 0})
summary={}
for name,rows in groups.items():
    ordered=sorted(rows,key=lambda x:x['handle_distance_m']); penetrations=[x for x in rows if x['inside_weapon'] and x['depth_if_inside_m']>.001]
    summary[name]={'vertices':len(rows),'minimum_distance_m':ordered[0]['handle_distance_m'],'closest_five_mean_m':sum(x['handle_distance_m'] for x in ordered[:5])/min(5,len(rows)),
        'vertices_inside_weapon_deeper_than_1mm':len(penetrations),'maximum_penetration_m':max((x['depth_if_inside_m'] for x in penetrations),default=0),'worst_inside':sorted(penetrations,key=lambda x:-x['depth_if_inside_m'])[:8]}
QA.mkdir(parents=True)
target=Vector((-.08,-.24,1.12))
for view,offset in [('front',(.30,-1,.15)),('back',(-.3,1,.15)),('side',(1,.1,.10))]:
    camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(QA/(view+'.png')); bpy.ops.render.render(write_still=True)
report={'side':'R','subject':'actual evaluated generated sword and core surfaces, not bone endpoints or a proxy cylinder','actual_handle_polygons':len(faces),'handle_axial_window_m':[-.112,.085],
    'inside_method':'odd/even ray against complete sword; depth from actual closest sword surface; 1mm diagnostic threshold, not art acceptance','groups':summary,'surface_contact_accepted':False}
(QA/'contact.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_CONTACT '+json.dumps({n:{k:v for k,v in r.items() if k!='worst_inside'} for n,r in summary.items()}))
