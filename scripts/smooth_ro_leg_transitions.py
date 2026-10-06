"""Same v001: test continuous leg/boot/pelvis transitions, preserving cloth mask.

Actual edges cross the z=.36 foot/leg cut with 32x stretch. This changes only
that demonstrated base-weight discontinuity and the z=.77 pelvis/leg cut; it
does not declare the cloth envelope correct or hide remaining intersections.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera,render_views
out=ROOT/'assets/processed/ro-swordsman-combo-r003/v001';qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001'
source=out/'ro_swordsman_hands_restored.blend';target=out/'ro_swordsman_continuous_base.blend'
assert not target.exists()
sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
scene=bpy.context.scene;body=bpy.data.objects['SM_RO_SourcePreservedBody'];rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'assign','dist_segment','solve','matrix','pose'}]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones};PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed v001 pose functions>','exec'),globals())
def smooth(a,b,v):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
coords=[tuple(v.co) for v in body.data.vertices];uv=[tuple(v.uv) for v in body.data.uv_layers.active.data]
changed=0
for v in body.data.vertices:
    groups={body.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}
    if any(n.startswith(('hand.','finger','thumb.','lower_arm.','upper_arm.')) for n in groups):continue
    if v.co.z>.90 or v.co.z<.27:continue
    if not all(n=='pelvis' or n=='tabard' or n.startswith(('coat.','upper_leg.','lower_leg.','foot.')) for n in groups):continue
    side='L' if v.co.x>=0 else 'R';z=v.co.z
    coat=groups.get('coat.'+side,0);tabard=groups.get('tabard',0);base=max(0,1-coat-tabard)
    pelvis=smooth(.70,.84,z);upper=smooth(.42,.63,z);leg=smooth(.29,.44,z)
    weights={'coat.'+side:coat,'tabard':tabard,'pelvis':base*pelvis,
             'upper_leg.'+side:base*(1-pelvis)*leg*upper,
             'lower_leg.'+side:base*(1-pelvis)*leg*(1-upper),
             'foot.'+side:base*(1-pelvis)*(1-leg)}
    # Up to four normalized influences, portable to the current export target.
    weights=dict(sorted(weights.items(),key=lambda row:-row[1])[:4]);assign(v,weights);changed+=1
assert coords==[tuple(v.co) for v in body.data.vertices] and uv==[tuple(v.uv) for v in body.data.uv_layers.active.data]
poses=[('overhead',.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98)),('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75)),('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6))]
stats=[];scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd) in enumerate(poses,1):
    pose(frame,h,rh,lh,sd);ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();edges=[]
    for e in body.data.edges:
        i,j=e.vertices;old=(body.data.vertices[i].co-body.data.vertices[j].co).length;new=(mesh.vertices[i].co-mesh.vertices[j].co).length
        if old>1e-6 and new>.1 and new/old>8:
            edges.append({'edge':e.index,'ratio':new/old,'length_m':new,'rest':[list(body.data.vertices[k].co) for k in [i,j]]})
    stats.append({'pose':name,'edges_over8x_and100mm':len(edges),'largest':sorted(edges,key=lambda row:-row['ratio'])[:5]});ob.to_mesh_clear()
    folder=qa/'preflight-continuous-base'/name;folder.mkdir(parents=True,exist_ok=False)
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95));render_views(qa/'continuous-base-views');camera()
bpy.ops.wm.save_as_mainfile(filepath=str(target));bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target.with_suffix('.glb')),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
assert sha==hashlib.sha256(source.read_bytes()).hexdigest()
report={'same_trial':'v001','started_utc':json.loads((qa.parent/'v001-start.json').read_text())['started_utc'],'source_sha256':sha,'changed_vertices':changed,
        'source_coordinates_unchanged':True,'UV_unchanged':True,'cloth_mask_unchanged':True,'stress_diagnostics':stats,'diagnostic_threshold_is_not_acceptance':True,
        'full_animation':False,'acceptance':'Await real preflight; existing cloth/leg intersections and eight nonmanifold edges remain separate checks.'}
(qa/'continuous-base-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
