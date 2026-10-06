"""v004: bounded anatomy/mesh-neighbor root transition, with fixed distal skin."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
import bpy
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign
from ro_hand_gate import segment_hit
from ro_review_common import camera,material
BASE=ROOT/'runs/qa/ro-swordsman-combo-r007';QA=BASE/'v004-root-weights';OUT=ROOT/'assets/processed/ro-swordsman-combo-r007/v004-root-weights'
start=json.loads((BASE/'v004-start.json').read_text());clock=json.loads((BASE/'phase-start.json').read_text())
frozen=json.loads((ROOT/start['frozen_masks']['path']).read_text());source=ROOT/start['source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not QA.exists() and not OUT.exists();QA.mkdir();OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];front=Vector((0,-1,0))
points=[v.co.copy() for v in ob.data.vertices];edges=[tuple(e.vertices) for e in ob.data.edges]
original={int(i):row for i,row in frozen['weights'].items()};semantic={int(i):row for i,row in frozen['semantic'].items()}
scale=json.loads((BASE/'v001-source-preparation/preparation.json').read_text())['uniform_scale']
neighbors={i:[] for i in range(len(points))}
for a,b in edges:
    distance=(points[a]-points[b]).length;neighbors[a].append((b,1/max(distance,1e-6)));neighbors[b].append((a,1/max(distance,1e-6)))
fourfinger={i for i,row in semantic.items() if row['branch']!='thumb'}
fixed_distal={i for i,row in original.items() if row.get('thumb_02',0)>1e-8 or row.get('thumb_03',0)>1e-8}
def reset():
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def rotate(name,angle,opposition=0):
    pb=rig.pose.bones[name];native=rig.data.bones[name].matrix_local.to_3x3()
    direction=(rig.data.bones[name].tail_local-rig.data.bones[name].head_local).normalized();axis=front.cross(direction).normalized()
    rotation=Matrix.Rotation(-angle,3,axis)
    if opposition:rotation=Matrix.Rotation(-opposition,3,Vector((0,0,1)))@rotation
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(native.inverted()@rotation@native).to_quaternion();bpy.context.view_layer.update()
def pose(amount,opposition=0):
    reset()
    for branch in ['finger1','finger2','finger3','finger4','thumb']:
        for j,factor in [(1,1),(2,1.4),(3,.85)]:rotate(f'{branch}_{j:02}',amount*factor,opposition if branch=='thumb' and j==1 else 0)
def actual(label,parameters):
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    assert [a.value for a in mesh.attributes['r007_original_point_id'].data]==list(range(len(points)))
    pts=[v.co.copy() for v in mesh.vertices];ts=[tuple(t.vertices) for t in mesh.loop_triangles];ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(pts,ts,all_triangles=True);cross=[]
    for i,j in tree.overlap(tree):
        if i>=j or set(ts[i])&set(ts[j]):continue
        a=[pts[k] for k in ts[i]];b=[pts[k] for k in ts[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(a,b),(b,a)] for k in range(3)):cross.append([i,j])
    ratios=[{'edge':[a,b],'ratio':(pts[b]-pts[a]).length/(points[b]-points[a]).length} for a,b in edges]
    return {'label':label,'parameters':parameters,'event_kind':'actual_skin_readback','observed_utc':now.isoformat(),
        'transverse_pairs':len(cross),'crossing_pairs':cross[:20],
        'degenerate_triangles':sum((pts[b]-pts[a]).cross(pts[c]-pts[a]).length<1e-12 for a,b,c in ts),
        'maximum_edge_stretch':max(r['ratio'] for r in ratios),'minimum_edge_ratio':min(r['ratio'] for r in ratios),
        'worst_stretch':sorted(ratios,key=lambda r:-r['ratio'])[:10],
        'fingerprint':hashlib.sha256(json.dumps({'positions':[list(p) for p in pts],'triangles':ts,'parameters':parameters},sort_keys=True).encode()).hexdigest()}
events=[];variants=[];best=None
for x_min in [-.025,-.035,-.045][:start['maximum_weight_variants']]:
    reset()
    domain={i for i,p in enumerate(points) if i not in fourfinger and i not in fixed_distal and
        .112*scale<p.z<.178*scale and x_min*scale<p.x<.078*scale}
    values={i:row.get('thumb_01',0) for i,row in original.items()}
    for _ in range(start['iterations_per_variant']):
        new=values.copy()
        for i in domain:
            average=sum(values[j]*w for j,w in neighbors[i])/sum(w for j,w in neighbors[i])
            new[i]=(1-start['relaxation'])*values[i]+start['relaxation']*average
        values=new
    weights={i:row.copy() for i,row in original.items()}
    for i in domain:weights[i]={'hand':1-values[i],'thumb_01':values[i]}
    for v in ob.data.vertices:assign(ob,v,weights[v.index])
    assert all(all(abs(weights[i].get(n,0)-original[i].get(n,0))<1e-9 for n in set(weights[i])|set(original[i])) for i in fourfinger|fixed_distal)
    pose(.30);event=actual('weight-variant',{'x_min_native_m':x_min,'curl_rad':.30,'iterations':100});events.append(event)
    jump=max(abs(weights[a].get('thumb_01',0)-weights[b].get('thumb_01',0)) for a,b in edges)
    variant={'x_min_native_m':x_min,'domain_vertices':sorted(domain),'maximum_neighbor_thumb01_jump':jump,'event':event}
    variants.append(variant)
    score=(event['transverse_pairs'],event['degenerate_triangles'],event['maximum_edge_stretch'])
    if best is None or score<best[0]:best=(score,weights,variant)
for v in ob.data.vertices:assign(ob,v,best[1][v.index])
reset();masks={'source':start['source'],'previous_masks':start['frozen_masks'],
    'domain_vertices':best[2]['domain_vertices'],'weight_solver':'100inverse-edge-distance Jacobi steps,0.7relaxation; fixed anatomy boundary',
    'selected_x_min_native_m':best[2]['x_min_native_m'],'weights':best[1],'original_pads':frozen['pads'],
    'geometry_UV_bone_positions_unchanged':True,'fourfinger_and_distal_thumb_weights_unchanged':True,
    'semantic_extension':'Previously unassigned thenar/palm vertices within fixed source domain may receive hand/thumb01 only; finger branches excluded',
    'maximum_influences':max(len([g for g in v.groups if g.weight>1e-8]) for v in ob.data.vertices)}
(QA/'frozen-weights.json').write_text(json.dumps(masks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
saved_materials=list(ob.data.materials);gray=material('RootWeightsGray',(.55,.55,.55));ob.data.materials.clear();ob.data.materials.append(gray)
def views(label):
    for n,loc in {'palm':(0,-1,.22),'side':(1,-.2,.24),'back':(0,1,.22)}.items():
        camera((loc,(.005,0,.18),.29));bpy.context.scene.render.filepath=str(QA/(label+'-'+n+'.png'));bpy.ops.render.render(write_still=True)
for label,amount,opposition in [('open',0,0),('small015',.15,0),('small030',.30,0),('opposition005',0,.05),('small030-opposition',.30,.15)]:
    pose(amount,opposition);events.append(actual(label,{'curl_rad':amount,'CMC_opposition_rad':opposition}));views(label)
reset();ob.data.materials.clear()
for m in saved_materials:ob.data.materials.append(m)
artifact=OUT/'right_hand_root_weights.blend';bpy.ops.wm.save_as_mainfile(filepath=str(artifact))
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'actual_variants':len(variants),
    'maximum_variants':start['maximum_weight_variants'],'variants':variants,'events':events,
    'selected_x_min_native_m':best[2]['x_min_native_m'],'joint_positions_unchanged':True,
    'small_motion_numeric_gate':all(not r['transverse_pairs'] and not r['degenerate_triangles'] for r in events[-5:]),
    'visual_acceptance':'pending actual views','material_gate':False,'known_crossisland_faces':16,
    'full_character_or_animation_accepted':False,
    'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
    'limitations':['Edge ratio used only to choose one diagnostic specimen, not a visual gate','Finite transverse test excludes adjacent folds and tangency','No contact/assembly/full300frame evidence']}
(QA/'weights.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RO_ROOT_WEIGHTS '+json.dumps({'selected':best[2]['x_min_native_m'],'numeric_gate':report['small_motion_numeric_gate'],'events':[(r['label'],r['transverse_pairs'],r['maximum_edge_stretch']) for r in events]}))
