"""Render and measure all frames of an existing failed candidate, without edits.

This completes stress-test evidence, not a new revision or acceptance bypass.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
version=sys.argv[sys.argv.index('--')+1]
if version not in {'v001','v002','v003','v004'}:raise ValueError('Unknown candidate')
master=ROOT/'assets/processed/ro-swordsman-combo'/version/'ro_swordsman_master.blend'
qa=ROOT/'runs/qa/ro-swordsman-combo'/version
before=hashlib.sha256(master.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(master),load_ui=False,use_scripts=False)
scene=bpy.context.scene
scene.render.resolution_x=scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.eevee.taa_render_samples=32
scene.frame_start=1;scene.frame_end=300;scene.render.fps=60
frames=qa/'frames-neutral';frames.mkdir(exist_ok=True)
meshes=[o for o in scene.objects if o.type=='MESH' and any(c.name=='COL_Character' for c in o.users_collection)]
observations=[];started=time.monotonic()
for f in range(1,301):
    scene.frame_set(f);graph=bpy.context.evaluated_depsgraph_get()
    points=[];feet={}
    for ob in meshes:
        evaluated=ob.evaluated_get(graph);data=evaluated.to_mesh()
        pts=[evaluated.matrix_world @ v.co for v in data.vertices];points.extend(pts)
        for side in ['L','R']:
            group=ob.vertex_groups.get('foot.'+side)
            if group:
                selected=[p for v,p in zip(ob.data.vertices,pts) if any(g.group==group.index and g.weight>.9 for g in v.groups)]
                if selected:feet[side]=min(feet.get(side,float('inf')),min(p.z for p in selected))
        evaluated.to_mesh_clear()
    observations.append({'frame':f,'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)],'weighted_foot_min_z_m':feet})
    scene.render.filepath=str(frames/('frame_%04d.png'%f));bpy.ops.render.render(write_still=True)
    if f%60==0:print('STRESS_FRAME '+str(f),flush=True)
after=hashlib.sha256(master.read_bytes()).hexdigest()
if before!=after:raise RuntimeError('Master drift during read-only test')
report={'master':str(master.relative_to(ROOT)),'sha256':before,'master_unchanged':True,'fps':60,'rendered_frames':300,'tool':bpy.app.version_string,'diagnostic_render':'640px/32samples; distinct from frozen1280px/64sample scoring views','elapsed_seconds':time.monotonic()-started,'frames':observations,'acceptance':'FAIL: observed severe split surface and deformation defects; VFX not implemented. Numeric bounds do not prove absence of collision/contact defects.'}
(qa/'full-animation-stress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STRESS_RENDER_COMPLETE '+json.dumps({k:v for k,v in report.items() if k!='frames'}))
