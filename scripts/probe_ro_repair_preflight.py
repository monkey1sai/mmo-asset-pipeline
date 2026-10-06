"""Actual evaluated mesh contact and additional preflight views, no master edits."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera
p=argparse.ArgumentParser();p.add_argument('--version',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.version not in {'v001','v002','v003'}:raise ValueError('Invalid version')
out=ROOT/'assets/processed/ro-swordsman-combo-r002'/a.version;qa=ROOT/'runs/qa/ro-swordsman-combo-r002'/a.version
master=out/'ro_repair_bind.blend';before=hashlib.sha256(master.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(master));rig=bpy.data.objects['ARM_RO_Swordsman']
for script,names in [('build_ro_swordsman.py',{'solve','bone_matrix','POSES'}),('rebuild_ro_articulation.py',{'REST','PARENTS','pose'})]:
    tree=ast.parse((ROOT/'scripts'/script).read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets) or script=='rebuild_ro_articulation.py' and isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and any(isinstance(x,ast.Name) and x.id=='side' for x in n.target.elts)]
    # Only the top-level REST-definition loop exists; no scene creation executes.
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<read-only pose probe>','exec'),globals())
def evaluated(ob):
    deps=bpy.context.evaluated_depsgraph_get();eo=ob.evaluated_get(deps);me=eo.to_mesh();vs=[eo.matrix_world@v.co for v in me.vertices];fs=[list(f.vertices) for f in me.polygons];eo.to_mesh_clear();return vs,fs
rows=[];scene=bpy.context.scene;scene.render.resolution_x=scene.render.resolution_y=960
for idx,label in [(2,'overhead'),(5,'downslash'),(7,'landing')]:
    target=POSES[idx];pose(target[0],target)
    gripvs,gripfs=evaluated(bpy.data.objects['SM_SwordGrip']);bvh=BVHTree.FromPolygons(gripvs,gripfs,all_triangles=False)
    contacts={}
    for side in ['L','R']:
        distances=[]
        for ob in bpy.context.scene.objects:
            if ob.name.startswith('SM_GloveFinger') and ob.name.endswith('_'+side):
                vs,_=evaluated(ob);distances.extend(bvh.find_nearest(v)[3] for v in vs)
        values=sorted(distances);contacts[side]={'closest_m':values[0],'closest_20_mean_m':sum(values[:20])/20,'method':'actual skinned glove finger surface vertices to actual evaluated sword grip triangle BVH; not target position identity'}
    feet={side:min(v.z for v in evaluated(bpy.data.objects['SM_Source_Boot_'+side])[0]) for side in ['L','R']}
    rows.append({'pose':label,'frame':target[0],'finger_to_actual_grip':contacts,'actual_boot_min_z':feet})
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(qa/'preflight'/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
    camera(((.7,-2,1.60),(0,0,1.50),.50));scene.render.filepath=str(qa/'preflight'/(label+'-face-close.png'));bpy.ops.render.render(write_still=True)
assert hashlib.sha256(master.read_bytes()).hexdigest()==before
(qa/'preflight-contact.json').write_text(json.dumps({'master_sha256':before,'evaluated_mesh_checks':rows,'master_unchanged':True,'art_or_deformation_acceptance':'requires visual review'},indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows))
