"""Complete source baseline, derived only by metric normalization; no repairs."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import stage, render_views
OUT=ROOT/'assets/processed/ro-swordsman-combo-r002/baseline'
QA=ROOT/'runs/qa/ro-swordsman-combo-r002/baseline'
OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)
source=ROOT/'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb'
expected='9350ee0a6cbe9af02bedabcc7ccee01153b7af90edc7f604dae67d205999e4c1'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH'); mw=ob.matrix_world.copy()
points=[mw@v.co for v in ob.data.vertices]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3))); hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
center=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z)); factor=1.74/(hi.z-lo.z)
for v in ob.data.vertices: v.co=(mw@v.co-center)*factor
ob.parent=None; ob.matrix_world=Matrix.Identity(4); ob.name='SM_RO_UnrepairedSource'
ob.data.update()
bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
top={'welded_vertices':len(bm.verts),'nonmanifold_after_exact_seam_weld':sum(not e.is_manifold for e in bm.edges)}; bm.free()
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_source_baseline.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)
report={'source_sha256':expected,'normalization':{'height_m':1.74,'ground_z':0,'units':'m','blender_up':'+Z','blender_forward':'-Y','glb_up':'+Y','glb_forward':'+Z'}, 'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons), 'meshes':1,'bones':0,'animations':0,'skill_effects':0,'topology':top,'images':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE'], 'observed_function_failure':'No rig/animation/effects exist; fused hands and weapon prevent articulated use. Static source is a failing but completely inspected baseline, not delivered.'}
stage(); render_views(QA)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_source_baseline.blend'))
report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in {'.blend','.glb'}}
(QA/'inspection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
print('RO_SOURCE_BASELINE '+json.dumps(report))
