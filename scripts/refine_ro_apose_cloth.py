"""Same v001 clock: replace speckled UV weight boundaries with coherent cloth.

Preserve the failed preflight and original source geometry. Bounded geometric
envelopes distinguish outer coat surfaces from central leg volumes; spatial
blends are smooth rather than hard per-texel labels. Still requires actual QA.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import shutil
import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera,render_views
out=ROOT/'assets/processed/ro-swordsman-combo-r003/v001';qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001'
archive=out/'attempt01-uv-mask';archive.mkdir(exist_ok=False)
for name in ['ro_swordsman_preflight.blend','ro_swordsman_preflight.glb']:
    shutil.copy2(out/name,archive/name)
shutil.copytree(qa,archive/'qa')
bpy.ops.wm.open_mainfile(filepath=str(out/'ro_swordsman_preflight.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;body=bpy.data.objects['SM_RO_SourcePreservedBody'];rig=bpy.data.objects['ARM_RO_Swordsman'];arm=rig.data
tree=ast.parse((ROOT/'scripts/build_ro_apose_candidate.py').read_text(encoding='utf-8'))
names={'assign','dist_segment','solve','matrix','pose'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
REST={b.name:(tuple(b.head_local),tuple(b.tail_local)) for b in arm.bones}
PARENTS={b.name:b.parent.name if b.parent else None for b in arm.bones}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed v001 pose functions>','exec'),globals())
def smooth(low,high,value):
    t=max(0,min(1,(value-low)/(high-low)));return t*t*(3-2*t)
old_uv=[tuple(d.uv) for d in body.data.uv_layers.active.data]
before_coords=[tuple(v.co) for v in body.data.vertices]
changed=0
for v in body.data.vertices:
    x,y,z=v.co;side='L' if x>=0 else 'R'
    if z>.92 or z<.36 or abs(x)>.38:continue
    # Outer coat wraps behind thighs and around lateral leg profiles. Keep the
    # central dark trouser columns deforming with legs; no geometry is cut.
    outer=max(smooth(.20,.27,abs(x)),smooth(.02,.075,y))
    front=smooth(.075,.14,-y)*(1-smooth(.10,.15,abs(x)))
    skirt=(1-smooth(.83,.92,z))*smooth(.34,.43,z)
    coat=outer*skirt
    tabard=front*skirt*(1-coat)
    base={}
    if z>.77:base={'pelvis':1}
    else:
        t=smooth(.40,.62,z);base={'upper_leg.'+side:t,'lower_leg.'+side:1-t}
    weights={n:w*(1-coat-tabard) for n,w in base.items()}
    weights['coat.'+side]=coat;weights['tabard']=tabard
    assign(v,weights);changed+=1
assert old_uv==[tuple(d.uv) for d in body.data.uv_layers.active.data]
assert before_coords==[tuple(v.co) for v in body.data.vertices]
# Keep texture-channel connections directly compatible with GLB. A shader-only
# MAXIMUM node is not a portable roughness contract and is removed from the trial.
for mat in body.data.materials:
    if not mat or not mat.use_nodes:continue
    bs=mat.node_tree.nodes.get('Principled BSDF');links=list(bs.inputs['Roughness'].links)
    if links and links[0].from_node.type=='MATH':
        node=links[0].from_node;up=list(node.inputs[0].links)
        if up:
            mat.node_tree.links.remove(links[0]);mat.node_tree.links.new(up[0].from_socket,bs.inputs['Roughness'])
        mat.node_tree.nodes.remove(node)
poses=[('overhead',.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98)),('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75)),('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6))]
scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd) in enumerate(poses,1):
    pose(frame,h,rh,lh,sd);folder=qa/'preflight-refined'/name;folder.mkdir(parents=True,exist_ok=False)
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95));render_views(qa/'refined-views')
camera();bpy.ops.wm.save_as_mainfile(filepath=str(out/'ro_swordsman_refined_preflight.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['COL_Character'].objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(out/'ro_swordsman_refined_preflight.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
report={'same_trial':'v001','same_started_utc':json.loads((ROOT/'runs/qa/ro-swordsman-combo-r003/v001-start.json').read_text())['started_utc'],
        'cause':'Hard per-texel cloth labels made a speckled skeletal deformation boundary visible in actual overhead/deep-crouch frames.',
        'changed_vertices':changed,'source_coordinates_unchanged':True,'UV_unchanged':True,'geometry_cuts':0,'full_animation':False,
        'failed_attempt_preserved':str(archive.relative_to(ROOT)),'new_hypothesis':'Coherent smoothly blended cloth volumes remove the discontinuous label artifacts; explicit panels may still be necessary.',
        'acceptance':'Await real preflight review; numeric smoothing is not pass.'}
(qa/'cloth-refinement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
