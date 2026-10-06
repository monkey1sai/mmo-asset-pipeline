"""Second stress run: actual300-frame evaluated surfaces, with immutable subjects.

Reports measured failures and potential intersections. No target-derived zero
contact, no automatic artistic PASS, and no edits to the input master/GLB.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import stage,camera
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--label',required=True);p.add_argument('--effects',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
src=(ROOT/a.input).resolve(strict=True)
if ROOT not in src.parents or src.suffix not in {'.blend','.glb'} or a.label not in {'neutral-master','neutral-roundtrip','with-effects','neutral-master-final','neutral-roundtrip-final','with-effects-final'}:raise ValueError('Invalid scoped stress input/label')
digest=hashlib.sha256(src.read_bytes()).hexdigest();QA=ROOT/'runs/qa/ro-swordsman-combo-r002/v003'/a.label;QA.mkdir(parents=True,exist_ok=False)
if src.suffix=='.blend':
    bpy.ops.wm.open_mainfile(filepath=str(src),load_ui=False,use_scripts=False)
    char=bpy.data.collections['COL_Character'];meshes=[ob for ob in char.objects if ob.type=='MESH']
    bpy.data.collections['COL_SkillEffects'].hide_render=not a.effects
else:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps=60;bpy.ops.import_scene.gltf(filepath=str(src))
    rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE');widgets={pb.custom_shape for pb in rig.pose.bones if pb.custom_shape}
    meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob not in widgets];stage()
rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE')
scene=bpy.context.scene;scene.render.resolution_x=scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.eevee.taa_render_samples=32;scene.render.fps=60;scene.frame_start=1;scene.frame_end=300
camera(((3.1,-5.5,2.9),(0,0,1.25),3.6))
folder=QA/'frames';folder.mkdir()
lookup={ob.name:ob for ob in meshes}
def actual(ob,graph):
    eo=ob.evaluated_get(graph);me=eo.to_mesh();vs=[eo.matrix_world@v.co for v in me.vertices];fs=[list(f.vertices) for f in me.polygons];eo.to_mesh_clear();return vs,fs
rows=[];start=time.monotonic();previous_hand=None;max_hand_step=0;overlaps=[];grip_fail=[];ground_fail=[];nonfinite=[]
for frame in range(1,301):
    scene.frame_set(frame-1 if src.suffix=='.glb' else frame);bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();geo={};allpoints=[]
    for ob in meshes:
        vs,fs=actual(ob,graph);geo[ob.name]=(vs,fs);allpoints.extend(vs)
    if not all(math.isfinite(v) for pt in allpoints for v in pt):nonfinite.append(frame)
    gv,gf=geo['SM_SwordGrip'];grip_bvh=BVHTree.FromPolygons(gv,gf,all_triangles=False)
    contacts={}
    for side in ['L','R']:
        distances=[]
        for name,(vs,_) in geo.items():
            if name.startswith('SM_GloveFinger') and name.endswith('_'+side):distances.extend(grip_bvh.find_nearest(v)[3] for v in vs)
        values=sorted(distances);contacts[side]={'closest_m':values[0],'closest20_mean_m':sum(values[:20])/20}
    if contacts['R']['closest20_mean_m']>.01 or 45<=frame<=125 and contacts['L']['closest20_mean_m']>.01:grip_fail.append(frame)
    feet={};support_centers={}
    for side in ['L','R']:
        vs,_=geo['SM_Source_Boot_'+side];floor=min(v.z for v in vs);feet[side]=floor
        bottom=[v for v in vs if v.z<=floor+.002];support_centers[side]=list(sum(bottom,Vector())/len(bottom))
    if min(feet.values())<-.003:ground_fail.append(frame)
    # Broad surface overlap investigation; intentional grip contacts excluded.
    hv,hf=geo['SM_Source_HeadHair'];bv,bf=geo['SM_SwordBlade'];head_bvh=BVHTree.FromPolygons(hv,hf,all_triangles=False);blade_bvh=BVHTree.FromPolygons(bv,bf,all_triangles=False)
    collision=len(head_bvh.overlap(blade_bvh))
    if collision:overlaps.append(frame)
    blade_min=min(v.z for v in bv);hand=rig.matrix_world@rig.pose.bones['hand.R'].matrix.translation
    if previous_hand is not None:max_hand_step=max(max_hand_step,(hand-previous_hand).length)
    previous_hand=hand
    rows.append({'frame':frame,'bounds':{'min':[min(v[i] for v in allpoints) for i in range(3)],'max':[max(v[i] for v in allpoints) for i in range(3)]},'actual_fingers_to_actual_grip':contacts,'boot_min_z_m':feet,'boot_bottom_centroid_m':support_centers,'blade_min_z_m':blade_min,'blade_head_bvh_overlap_count':collision,'right_hand_origin_m':list(hand)})
    scene.render.filepath=str(folder/f'frame_{frame:04d}.png');bpy.ops.render.render(write_still=True)
    if frame%60==0:print('RO_SECOND_STRESS_FRAME '+str(frame),flush=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==digest
report={'subject':src.relative_to(ROOT).as_posix(),'subject_sha256':digest,'subject_unchanged':True,'tool':bpy.app.version_string,'fps':60,'frames':300,'sampling_seconds':[0,299/60],'playback_seconds':5,'render_protocol':'640x640 Eevee32samples; wider full-weapon frame. Diagnostic only, fixed scoring views remain1280x1280/64samples.','effects_enabled':a.effects,'elapsed_seconds':time.monotonic()-start,'bone_count':len(rig.data.bones),'mesh_count':len(meshes),'nonfinite_frames':nonfinite,'grip_threshold_10mm_failure_frames':grip_fail,'ground_below_minus3mm_frames':ground_fail,'blade_head_potential_surface_overlap_frames':overlaps,'max_right_hand_origin_step_m_per_frame':max_hand_step,'note':'Contact is actual evaluated mesh/BVH. Potential intersections, foot sliding/support and all visual frames require review; no automatic art/deformation/animation PASS.','observations':rows}
(QA/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_SECOND_STRESS_COMPLETE '+json.dumps({k:v for k,v in report.items() if k!='observations'}))
