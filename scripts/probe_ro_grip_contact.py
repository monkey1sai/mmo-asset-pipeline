"""Actual glove-to-grip surface distances and bounded thumb opposition probe."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera
path=ROOT/'assets/processed/ro-swordsman-combo-r003/v001/ro_swordsman_continuous_base.blend';sha=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data;body=bpy.data.objects['SM_RO_SourcePreservedBody']
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pose functions>','exec'),globals())
pose(1,.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98))
sd=Vector((0,-.2,.98)).normalized();rotation=Vector((0,-1,0)).rotation_difference(sd).to_matrix().to_4x4()
pb=rig.pose.bones['hand.R'];wrist=pb.head.copy();m=rotation@arm.bones['hand.R'].matrix_local;m.translation=wrist;pb.matrix=m;bpy.context.view_layer.update()
location=pb.matrix@(arm.bones['hand.R'].matrix_local.inverted()@Vector(REST['sword'][0]))
rig.pose.bones['sword'].matrix=matrix(location,location+sd*.95,Vector((0,1,0)));bpy.context.view_layer.update()
groups={n:[] for n in ['thumb']+['finger'+str(i) for i in range(1,5)]}
for v in body.data.vertices:
    for name in groups:
        total=sum(g.weight for g in v.groups if body.vertex_groups[g.group].name.startswith(name+'.R') or name.startswith('finger') and body.vertex_groups[g.group].name.startswith(name+'.R'))
        if total>.5:groups[name].append(v.index)
grip=bpy.data.objects['SM_SwordGrip'];grip_eval=grip.evaluated_get(bpy.context.evaluated_depsgraph_get());gm=grip_eval.to_mesh();gm.calc_loop_triangles()
bvh=BVHTree.FromPolygons([grip_eval.matrix_world@v.co for v in gm.vertices],[tuple(t.vertices) for t in gm.loop_triangles],all_triangles=True)
grip_eval.to_mesh_clear()
def measure():
    ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();result={}
    for name,indices in groups.items():
        distances=sorted(bvh.find_nearest(ob.matrix_world@mesh.vertices[i].co)[3] for i in indices)
        result[name]={'selected_vertices':len(indices),'min_m':min(distances) if distances else None,
                      'p10_m':distances[int(len(distances)*.1)] if distances else None,
                      'p25_m':distances[int(len(distances)*.25)] if distances else None}
    ob.to_mesh_clear();return result
tests=[]
for angle in [0,.5,1.0,1.4]:
    for joint,factor in [('_01',1),('_02',.6)]:
        name='thumb.R'+joint;pb=rig.pose.bones[name];rest=arm.bones[name].matrix_local.to_3x3();pb.rotation_mode='QUATERNION'
        pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation(angle*factor,3,'Y')@rest).to_quaternion()
    bpy.context.view_layer.update();tests.append({'thumb_radians':angle,'actual_surface_distances':measure()})
best=min(tests,key=lambda r:r['actual_surface_distances']['thumb']['p10_m'])
angle=best['thumb_radians']
for joint,factor in [('_01',1),('_02',.6)]:
    name='thumb.R'+joint;pb=rig.pose.bones[name];rest=arm.bones[name].matrix_local.to_3x3()
    pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation(angle*factor,3,'Y')@rest).to_quaternion()
bpy.context.view_layer.update()
folder=ROOT/'runs/qa/ro-swordsman-combo-r003/v001/grip-contact-probe';folder.mkdir(exist_ok=False)
scene.render.resolution_x=scene.render.resolution_y=960
for view,offset in [('palm',(-.8,-1,.2)),('back',(.8,.7,.3)),('side',(-1,.2,.1))]:
    camera((tuple(location+Vector(offset)),tuple(location),.38));scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
report={'subject_sha256':sha,'saved_master':False,'changed_weights':False,'thumb_grid':tests,'selected_thumb_radians':angle,
        'method':'Evaluated body mesh vertices with >50% digit influence to actual evaluated grip triangles via BVH. Percentiles of multiple vertices, no bone-origin contact assertion.',
        'limits':'Distances alone do not prove opposed grasp, no penetration, or all skill poses. Actual close views and other poses required.'}
(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');assert sha==hashlib.sha256(path.read_bytes()).hexdigest();print(json.dumps(report))
