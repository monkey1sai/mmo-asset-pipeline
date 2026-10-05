"""v002 dependency: remove proven tiny fins, then refit preserved equipment to new core."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import render_views
SOURCE=ROOT/'assets/processed/ro-swordsman-combo-r005/core-source-comparison/source_comparison.blend'
SOURCE_SHA='fe76a7e15c5f8a91e4d78c6722a31f326d49df1fbd6eda888c567474a663fd59'
GEAR=ROOT/'assets/processed/ro-swordsman-combo-r005/v001-fit-tailored/ro_tailored_fit.blend'
GEAR_SHA='eaf01613d30cddbf44a951236aabdbfd3931f309da8e0791ef5924b309993a66'
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v002-fit'
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-fit'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def center_at(core,z,minimum_x):
    points=[v.co for v in core.data.vertices if v.co.x>minimum_x and abs(v.co.z-z)<.009]
    if len(points)<8: raise RuntimeError('Landmark section insufficient')
    return Vector([(min(p[i] for p in points)+max(p[i] for p in points))/2 for i in range(3)])
if OUT.exists() or QA.exists() or sha(SOURCE)!=SOURCE_SHA or sha(GEAR)!=GEAR_SHA:
    raise RuntimeError('Preserve earlier sources/versions')
phase=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-start.json').read_text())
now=datetime.now(timezone.utc)
if (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds'] or (now-datetime.fromisoformat(start['started_utc'])).total_seconds()>=phase['budget']['trial_seconds']:
    raise RuntimeError('Original experiment budget exhausted')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
core=bpy.data.objects['SM_RO_Core_Fallback_Source']
bpy.data.objects.remove(bpy.data.objects['SM_RO_Core_Batch_Source'],do_unlink=True)
core.name='SM_RO_core'; core.hide_render=False
bm=bmesh.new(); bm.from_mesh(core.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
fins=[f for f in bm.faces if len(f.verts)==3 and all(v.co.z>1.46 for v in f.verts) and sum(e.is_boundary for e in f.edges)==2 and sum(len(e.link_faces)==3 for e in f.edges)==1]
if len(fins)!=4 or any(f.calc_area()>.00003 for f in fins):
    raise RuntimeError('Unexpected topology: inspect instead of generic deletion/fill')
removed=[{'positions':[list(v.co) for v in f.verts],'area_m2':f.calc_area()} for f in fins]
bmesh.ops.delete(bm,geom=fins,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
nonmanifold=sum(not e.is_manifold for e in bm.edges)
if nonmanifold: raise RuntimeError('Local fin repair did not restore manifold: preserve diagnostics')
bm.to_mesh(core.data); bm.free(); core.data.update()
char=bpy.data.collections.new('COL_Character'); bpy.context.scene.collection.children.link(char)
for col in list(core.users_collection): col.objects.unlink(core)
char.objects.link(core)
names=['SM_RO_cuirass','SM_RO_coat','SM_RO_pauldron.R','SM_RO_pauldron.L','SM_RO_bracer.R','SM_RO_bracer.L','SM_RO_sword']
with bpy.data.libraries.load(str(GEAR),link=False) as (src,dst): dst.objects=names
gears={ob.name:ob for ob in dst.objects}
for ob in gears.values():
    char.objects.link(ob); ob.parent=None; ob.hide_render=False
    if ob.modifiers: raise RuntimeError('Gear source unexpectedly rigged')
wrist=center_at(core,.948,.33)
elbow=center_at(core,1.145,.27)
shoulder=Vector((.205,.07,1.33))
landmarks={'L':{'wrist':list(wrist),'elbow':list(elbow),'shoulder':list(shoulder)},'R':{k:[-v[0],v[1],v[2]] for k,v in {'wrist':wrist,'elbow':elbow,'shoulder':shoulder}.items()}}
fit_reports={}
for side,sign in [('R',-1),('L',1)]:
    ob=gears['SM_RO_bracer.'+side]
    array=np.array([list(v.co) for v in ob.data.vertices]); center=Vector(array.mean(axis=0))
    vals,axes=np.linalg.eigh(np.cov((array-np.array(center)).T)); native=Vector(axes[:,np.argmax(vals)])
    if native.z<0: native=-native
    desired=(Vector(landmarks[side]['elbow'])-Vector(landmarks[side]['wrist'])).normalized()
    rotation=native.rotation_difference(desired).to_matrix()
    destination=(Vector(landmarks[side]['elbow'])+Vector(landmarks[side]['wrist']))/2
    for v in ob.data.vertices: v.co=destination+rotation@(v.co-center)
    ob.data.update(); fit_reports[ob.name]={'source_axis':list(native),'new_axis':list(desired),'destination':list(destination),'rigid_transform':True}
    paul=gears['SM_RO_pauldron.'+side]
    offset=Vector(landmarks[side]['shoulder'])-Vector((sign*.232,.015,1.34))
    for v in paul.data.vertices: v.co+=offset
    paul.data.update(); fit_reports[paul.name]={'translation':list(offset)}
OUT.mkdir(parents=True); QA.mkdir(parents=True)
render_views(QA)
bpy.ops.object.select_all(action='DESELECT')
for ob in char.objects: ob.select_set(True)
bpy.context.view_layer.objects.active=core
bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_core_fit.glb'),export_format='GLB',use_selection=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_core_fit.blend'))
tri=sum(len(f.vertices)-2 for ob in char.objects for f in ob.data.polygons)
if tri!=58868 or tri>60000: raise RuntimeError('Unexpected whole-character triangle budget')
report={'candidate':'v002','stage':'source repair and gear fit dependency, not acceptance','source_sha256':SOURCE_SHA,'gear_source_sha256':GEAR_SHA,
    'tiny_attached_fin_faces_removed':removed,'core_triangles':sum(len(f.vertices)-2 for f in core.data.polygons),'triangles':tri,
    'position_weld_tolerance_m':1e-6,'nonmanifold_edges':nonmanifold,'uv_loop_coordinates_on_retained_faces_preserved_by_bmesh':True,
    'landmarks':landmarks,'gear_transforms':fit_reports,'geometry_gaps_filled':0,'rig_accepted':False,'animation_accepted':False,
    'source_files_unchanged':sha(SOURCE)==SOURCE_SHA and sha(GEAR)==GEAR_SHA,
    'artifacts':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir()]}
(QA/'fit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_CORE_FIT '+json.dumps({'triangles':tri,'fin_faces_removed':len(removed),'nonmanifold_edges':nonmanifold,'landmarks':landmarks}))
