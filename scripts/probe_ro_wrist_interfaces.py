"""Read-only actual wrist boundaries/collider sections before v006 changes."""
from pathlib import Path
import hashlib,json,sys
import bpy,bmesh
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure
from ro_hand_gate import evaluated,segment_hit
from mathutils.bvhtree import BVHTree
QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
OUT=QA/'wrist-interface-diagnosis.json'; assert not OUT.exists()
source=ROOT/'assets/processed/ro-swordsman-combo-r006/v005-thumb-wrist/ro_thumb_contact_checkpoint.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json'])
glove=bpy.data.objects['SM_RO_glove.R']; core=bpy.data.objects['SM_RO_core']; bracer=bpy.data.objects['SM_RO_bracer.R']
anatomy=json.loads((QA/'v001-generated-glove/anatomy-and-masks.json').read_text())
rotation=Matrix(anatomy['rotation']); wrist=Vector(state['rest']['hand.R'][0]); source_wrist=Vector(anatomy['source_wrist'])
axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized()
def loops(ob):
    bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    edges=[e for e in bm.edges if e.is_boundary]; unseen=set(edges); out=[]
    while unseen:
        seed=unseen.pop(); found={seed}; verts=set(seed.verts); stack=list(seed.verts)
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                if e in unseen:
                    unseen.remove(e); found.add(e)
                    for v2 in e.verts:
                        if v2 not in verts: verts.add(v2); stack.append(v2)
        out.append({'vertices':len(verts),'edges':len(found),'closed_simple':all(sum(e in found for e in v.link_edges)==2 for v in verts),
                    'centroid':list(sum((v.co for v in verts),Vector())/len(verts)),
                    'points':[list(v.co) for v in verts],
                    'axial_min_max':[min((v.co-wrist).dot(axis) for v in verts),max((v.co-wrist).dot(axis) for v in verts)]})
    info={'welded_vertices':len(bm.verts),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'boundary_loops':out}; bm.free(); return info
sections=[]
for t in [-.12,-.09,-.06,-.04,-.02,0,.02,.04,.06]:
    plane=wrist+axis*t; row={'axial_from_wrist_m':t}
    for ob in [glove,core,bracer]:
        points=[]
        for e in ob.data.edges:
            a,b=(ob.data.vertices[i].co for i in e.vertices)
            if min((p-plane).length for p in [a,b])>.15: continue
            da,db=(a-plane).dot(axis),(b-plane).dot(axis)
            if da*db>0 or abs(da-db)<1e-9: continue
            points.append(a.lerp(b,da/(da-db)))
        radius=[(p-plane).length for p in points]
        row[ob.name]={'points':len(points),'radial_min_max_m':[min(radius),max(radius)] if radius else None,
                      'positions':[list(p) for p in points]}
    sections.append(row)
params=json.loads(rig['r006_independent_grip_ik_parameters']); glove.data.shape_keys.key_blocks['GripContact_R'].value=1
configure(rig,state,params); gp,gt,_=evaluated(glove); ap,at,_=evaluated(bracer)
a=BVHTree.FromPolygons(gp,gt,all_triangles=True); b=BVHTree.FromPolygons(ap,at,all_triangles=True)
cross=[]; used=set()
for i,j in a.overlap(b):
    x=[gp[k] for k in gt[i]]; y=[ap[k] for k in at[j]]
    if any(segment_hit(left[k],left[(k+1)%3],right) is not None for left,right in [(x,y),(y,x)] for k in range(3)):
        used.update(at[j]); cross.append([i,j])
bracer_rest=[{'id':i,'position':list(bracer.data.vertices[i].co),'axial_from_wrist_m':(bracer.data.vertices[i].co-wrist).dot(axis),
             'radius_from_axis_m':((bracer.data.vertices[i].co-wrist)-axis*(bracer.data.vertices[i].co-wrist).dot(axis)).length} for i in sorted(used)]
result={'source':{'path':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},
        'wrist':list(wrist),'forearm_axis':list(axis),'rest_bones':{n:state['rest'][n] for n in ['lower_arm.R','hand.R']},
        'actual_topology':{ob.name:loops(ob) for ob in [core,glove,bracer]},'sections':sections,
        'grip_bracer_crossing_pairs':len(cross),'colliding_bracer_rest_vertices':bracer_rest,
        'interpretation':'diagnostic only; no geometry edited, no acceptance claim'}
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['sections','colliding_bracer_rest_vertices','actual_topology']}))
print(json.dumps({'topology':{n:{k:v for k,v in r.items() if k!='boundary_loops'}|{'loops':[{'vertices':l['vertices'],'closed_simple':l['closed_simple'],'centroid':l['centroid'],'axial_min_max':l['axial_min_max']} for l in r['boundary_loops']]} for n,r in result['actual_topology'].items()},
                  'collider_axial_range':[min(v['axial_from_wrist_m'] for v in bracer_rest),max(v['axial_from_wrist_m'] for v in bracer_rest)] if bracer_rest else None}))
