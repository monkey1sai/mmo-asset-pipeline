"""Actual triangle/source/branch locations and full-bone vector boundary jump."""
from datetime import datetime,timezone
from collections import Counter
import sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
result=read(QA/'v002-direction/result.json');large=read(QA/'v002-functional-curl/result.json');contract=read(QA/'local-contract.json')
folder=QA/'v002-failure-locations';assert not folder.exists();folder.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
ww=weights(ob);rest=geometry(ob);domain=set(contract['anatomical_domain_ids']);semantic=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['semantic']
boundary=[]
for a,b in rest['edges']:
    if (a in domain)==(b in domain):continue
    names=set(ww[a])|set(ww[b]);diff=[ww[a].get(n,0)-ww[b].get(n,0) for n in names]
    boundary.append({'edge':[a,b],'full_bone_L1':sum(abs(d) for d in diff),'full_bone_L2':sum(d*d for d in diff)**.5,
                     'weight_vectors':[ww[a],ww[b]],'source_ids':[rest['point_attributes']['r007_source_point_id'][i] for i in [a,b]]})
ob.data.materials.clear();ob.data.materials.append(material('r008LocateGray',(.55,.55,.55)))
events=[]
for row in large['events']:
    for n,m in row['actual_basis'].items():rig.pose.bones[n].matrix_basis=Matrix(m)
    bpy.context.view_layer.update()
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    points=[v.co.copy() for v in mesh.vertices];triangles=[tuple(t.vertices) for t in mesh.loop_triangles];faceids=[t.polygon_index for t in mesh.loop_triangles];ev.to_mesh_clear()
    counts=Counter();crosses=[];bad_lines=[]
    for a,b in row['crossings']:
        ids=[list(triangles[a]),list(triangles[b])]
        branches=[sorted({semantic.get(str(i),{'branch':'palm'})['branch'] for i in group}) for group in ids]
        counts[str(branches)]+=1
        crosses.append({'evaluated_triangle_pair':[a,b],'polygon_pair':[faceids[a],faceids[b]],'point_ids':ids,'branches':branches,
                        'source_ids':[[rest['point_attributes']['r007_source_point_id'][i] for i in group] for group in ids],
                        'positions':[[list(points[i]) for i in group] for group in ids]})
        for group in ids:bad_lines.append([points[i] for i in group]+[points[group[0]]])
    wire=line_object('ActualCrossingTriangles',bad_lines,(1,.04,.02),.00045)
    render(folder,row['label'],['side','palm'])
    bpy.data.objects.remove(wire,do_unlink=True)
    events.append({'label':row['label'],'actual_crossing_count':row['transverse_pairs'],'saved_representative_pair_count':len(crosses),'representative_branches':dict(counts),'pairs':crosses})
save(folder/'locations.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'events':events,'full_bone_boundary_vectors':boundary,
 'representative_limit':20,'all_pair_count_reported_from_actualreadback':True,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R008_LOCATIONS '+json.dumps([(r['label'],r['representative_branches']) for r in events]))
