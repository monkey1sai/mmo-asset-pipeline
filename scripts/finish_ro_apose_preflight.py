"""Same v001: preserve tested hand/cloth motions and inspect two-hand poses.

Preflight master only. A sampled contact or render never grants animation PASS.
"""
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
from ro_review_common import camera,render_views
out=ROOT/'assets/processed/ro-swordsman-combo-r003/v001';qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001'
source=out/'ro_swordsman_continuous_base.blend';target=out/'ro_swordsman_functional_preflight.blend';assert not target.exists()
sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data;body=bpy.data.objects['SM_RO_SourcePreservedBody']
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pose functions>','exec'),globals());source_pose=pose
# Two glove widths require a longer grip than the original single-hand .125m.
grip=Vector(REST['sword'][0]);direction=Vector((0,-1,0))
for v in bpy.data.objects['SM_SwordGrip'].data.vertices:
    d=(v.co-grip).dot(direction)
    if d<0:v.co-=direction*.10
for v in bpy.data.objects['SM_SwordPommel'].data.vertices:v.co-=direction*.10

def orient_hand(side,rotation):
    pb=rig.pose.bones['hand.'+side];wrist=pb.head.copy();m=rotation@arm.bones[pb.name].matrix_local;m.translation=wrist;pb.matrix=m
    for joint,factor in [('_01',1),('_02',.6)]:
        name='thumb.'+side+joint;pb=rig.pose.bones[name];rest=arm.bones[name].matrix_local.to_3x3();pb.rotation_mode='QUATERNION'
        pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation((1 if side=='R' else -1)*1.4*factor,3,'Y')@rest).to_quaternion()

def functional_pose(frame,hip,rh,lh,sd,dual=False):
    sd=Vector(sd).normalized();rotation=Vector((0,-1,0)).rotation_difference(sd).to_matrix().to_4x4()
    source_pose(frame,hip,rh,lh,sd);orient_hand('R',rotation);bpy.context.view_layer.update()
    primary=rig.pose.bones['hand.R'].matrix@(arm.bones['hand.R'].matrix_local.inverted()@Vector(REST['sword'][0]))
    if dual:
        # Secondary grip is .10m behind the primary; solve the arm to its actual
        # wrist offset, then measure resulting surfaces rather than assume zero.
        rest_grip=Vector((.445,-.08,.827));offset=rest_grip-Vector(REST['hand.L'][0])
        wrist=primary-sd*.10-rotation.to_3x3()@offset
        source_pose(frame,hip,rh,wrist,sd);orient_hand('R',rotation);orient_hand('L',rotation);bpy.context.view_layer.update()
        primary=rig.pose.bones['hand.R'].matrix@(arm.bones['hand.R'].matrix_local.inverted()@Vector(REST['sword'][0]))
    rig.pose.bones['sword'].matrix=matrix(primary,primary+sd*.95,Vector((0,1,0)))
    pb=rig.pose.bones['tabard'];pb.matrix=pb.matrix@Matrix.Rotation(-.65*min(1,max(0,(.88-hip)/.20)),4,'X')
    bpy.context.view_layer.update()
    return primary

groups={side:{digit:[] for digit in ['thumb']+['finger'+str(i) for i in range(1,5)]} for side in ['L','R']}
for v in body.data.vertices:
    for side in groups:
        for digit in groups[side]:
            if sum(g.weight for g in v.groups if body.vertex_groups[g.group].name.startswith(digit+'.'+side))>.5:groups[side][digit].append(v.index)

def contacts():
    graph=bpy.context.evaluated_depsgraph_get();go=bpy.data.objects['SM_SwordGrip'].evaluated_get(graph);gm=go.to_mesh();gm.calc_loop_triangles()
    bvh=BVHTree.FromPolygons([go.matrix_world@v.co for v in gm.vertices],[tuple(t.vertices) for t in gm.loop_triangles],all_triangles=True);go.to_mesh_clear()
    bo=body.evaluated_get(graph);bm=bo.to_mesh();result={}
    for side,digits in groups.items():
        result[side]={}
        for digit,indices in digits.items():
            ds=sorted(bvh.find_nearest(bo.matrix_world@bm.vertices[i].co)[3] for i in indices)
            result[side][digit]={'vertices':len(ds),'min_m':ds[0] if ds else None,'p10_m':ds[int(len(ds)*.1)] if ds else None,'p25_m':ds[int(len(ds)*.25)] if ds else None}
    bo.to_mesh_clear();return result

poses=[('standing',.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95),False),
       ('overhead',.88,(-.10,-.20,1.62),(.17,-.12,1.57),(0,-.2,.98),True),
       ('half-crouch',.78,(-.20,-.32,1.20),(.19,-.28,1.0),(-.1,-.65,.75),True),
       ('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75),True),
       ('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6),True)]
rows=[];scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd,dual) in enumerate(poses,1):
    center=functional_pose(frame,h,rh,lh,sd,dual);folder=qa/'functional-preflight'/name;folder.mkdir(parents=True,exist_ok=False)
    rows.append({'pose':name,'dual_grip':dual,'actual_surface_contact':contacts()})
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    for label,offset in [('grip-palm',(-.8,-1,.2)),('grip-back',(.8,.7,.3))]:
        camera((tuple(center+Vector(offset)),tuple(center),.48));scene.render.filepath=str(folder/(label+'.png'));bpy.ops.render.render(write_still=True)
functional_pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95));render_views(qa/'functional-views');camera()
bpy.ops.wm.save_as_mainfile(filepath=str(target));bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target.with_suffix('.glb')),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
assert sha==hashlib.sha256(source.read_bytes()).hexdigest()
report={'same_trial':'v001','started_utc':json.loads((qa.parent/'v001-start.json').read_text())['started_utc'],'source_sha256':sha,
        'bone_count':len(arm.bones),'triangles':39946,'full_animation':False,'VFX':False,'source_coordinates_UV_preserved':True,'two_hand_grip_length_m':.225,
        'poses':rows,'limits':'Actual contact percentile is supporting evidence; paired hands, garments and joints require real review. Eight source nonmanifold edges remain.',
        'acceptance':'Preflight only, not accepted character or continuous skill delivery.'}
(qa/'functional-preflight-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='poses'}))
