"""v002 bounded pose calibration using true handle surfaces, followed by manual review."""
from datetime import datetime,timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import pose
from ro_review_common import camera,render_views
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v002-contact-calibrated'
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-contact-calibrated'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-rig-minimal/preflight.json').read_text())
artifact=next(x for x in previous['artifacts'] if x['path'].endswith('.blend')); source=ROOT/artifact['path']
if OUT.exists() or QA.exists() or hashlib.sha256(source.read_bytes()).hexdigest()!=artifact['sha256']: raise RuntimeError('Preserve source/prior calibration')
phase=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text()); start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-start.json').read_text())
def guard():
    now=datetime.now(timezone.utc)
    if (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds'] or (now-datetime.fromisoformat(start['started_utc'])).total_seconds()>=phase['budget']['trial_seconds']: raise RuntimeError('Original experiment budget exhausted')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']; state=json.loads(rig['state_json'])
original=copy.deepcopy(state); palms={}; base_offsets={}; groups={}; log=[]
for side in ['R','L']:
    heads=[Vector(v) for v in state['measurements'][side]['knuckles']]; tips=[Vector(v) for v in state['measurements'][side]['tips']]
    down=sum((t-h for t,h in zip(tips,heads)),Vector()).normalized()
    width=heads[-1]-heads[0]
    if width.x<0: width=-width
    width=(width-down*width.dot(down)).normalized(); front=down.cross(width).normalized()
    matrix=Matrix((width,front,down)).transposed()
    if front.y>0 or abs(matrix.determinant()-1)>1e-6: raise RuntimeError('Invalid measured digit frame')
    state['hand_frames'][side]={'width':list(width),'front':list(front),'down':list(down),'determinant':matrix.determinant(),'down_method':'mean measured four finger tip minus knuckle, rather than wrist-to-knuckle direction'}
    palms[side]=sum(heads,Vector())/4; base_offsets[side]=[.033,.021]
    groups[side]={}
    for v in core.data.vertices:
        if not ((v.co.x>0)==(side=='L') and abs(v.co.x)>.34 and v.co.z<.96): continue
        w={core.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}; n=max(w,key=w.get)
        part='palm' if n=='hand.'+side else 'thumb' if n.startswith('thumb.'+side) else n.split('.')[0] if n.startswith('finger') and '.'+side+'_' in n else None
        if part: groups[side].setdefault(part,[]).append(v.index)
state['finger_angles']={s:{str(i):[.85,1.105] for i in range(1,5)} for s in ['R','L']}
state['thumb_offsets']={'R':[-.020,.018,-.004],'L':[.020,.018,-.004]}
evaluations=0
def set_grip(side,front_offset,down_offset):
    frame=state['hand_frames'][side]
    state['grips'][side]=list(palms[side]+Vector(frame['front'])*front_offset+Vector(frame['down'])*down_offset)

def rebuild_sword_rest():
    # Only this preserved generated sword changes rigid placement; no topology edits.
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    old_axis=Vector(original['weapon_axis_in_rest']); new_axis=-Vector(state['hand_frames']['R']['width'])
    transform=old_axis.rotation_difference(new_axis).to_matrix()
    old_origin=Vector(original['grips']['R']); new_origin=Vector(state['grips']['R'])
    for v,raw in zip(sword.data.vertices,sword_original): v.co=new_origin+transform@(raw-old_origin)
    sword.data.update()
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
    bone=rig.data.edit_bones['sword']; bone.head=new_origin; bone.tail=new_origin+new_axis*.8
    bpy.ops.object.mode_set(mode='OBJECT')
    state['rest']['sword']=[list(new_origin),list(new_origin+new_axis*.8)]; state['weapon_axis_in_rest']=list(new_axis)
    bpy.context.view_layer.update()
sword_original=[v.co.copy() for v in sword.data.vertices]
for side in ['R','L']: set_grip(side,*base_offsets[side])
rebuild_sword_rest()

def evaluate(side):
    global evaluations
    guard(); evaluations+=1
    if evaluations>160: raise RuntimeError('Bounded surface calibration exhausted')
    pose(rig,state,.89,(-.08 if side=='R' else .08,-.29,1.12),(0,-.1,.995),two_hands=False,active_side=side)
    deps=bpy.context.evaluated_depsgraph_get(); co=core.evaluated_get(deps); so=sword.evaluated_get(deps)
    points=[so.matrix_world@v.co for v in so.data.vertices]
    center=rig.pose.bones['sword'].head; axis=(rig.pose.bones['sword'].tail-center).normalized()
    faces=[list(f.vertices) for f in so.data.polygons if all(-.112<(points[i]-center).dot(axis)<.085 for i in f.vertices)]
    tree=BVHTree.FromPolygons(points,faces)
    result={}; loss=0
    for part,indices in groups[side].items():
        distances=[]; inside_depths=[]
        for index in indices:
            p=co.matrix_world@co.data.vertices[index].co
            hit,normal,face,d=tree.find_nearest(p)
            if hit is None: raise RuntimeError('Missing actual handle nearest point')
            distances.append(d)
            # Local signed nearest is an optimization diagnostic; final odd/even verification is separate.
            if (p-hit).dot(normal)<0 and d<.023: inside_depths.append(d)
        closest=sum(sorted(distances)[:5])/min(5,len(distances)); depth=max(inside_depths,default=0)
        target=.002; weight=2 if part=='palm' else 1
        loss+=weight*abs(closest-target)+8*depth+sum(inside_depths)*.5
        result[part]={'closest5_mean_m':closest,'max_local_signed_penetration_m':depth,'local_signed_inside_count':len(inside_depths)}
    return loss,result

OUT.mkdir(parents=True); QA.mkdir(parents=True)
for side in ['R','L']:
    baseline_loss,baseline=evaluate(side); best=baseline_loss; chosen=list(base_offsets[side])
    # Nine bounded grip candidates, then per-joint coordinate search. Maximum 80 evaluations/side.
    for f in [.003,.018,.033]:
        for d in [-.012,.006,.021]:
            set_grip(side,f,d)
            if side=='R': rebuild_sword_rest()
            loss,metrics=evaluate(side); log.append({'side':side,'parameter':'grip_offset','value':[f,d],'loss':loss})
            if loss<best: best=loss; chosen=[f,d]
    base_offsets[side]=chosen; set_grip(side,*chosen)
    if side=='R': rebuild_sword_rest()
    best,metrics=evaluate(side)
    for i in range(1,5):
        for joint,values in [(0,[.55,.85,1.10,1.35]),(1,[.75,1.05,1.35,1.55])]:
            old=state['finger_angles'][side][str(i)][joint]; selected=old
            for value in values:
                angles=state['finger_angles'][side][str(i)]
                if value+angles[1-joint]>3.0: continue
                angles[joint]=value
                loss,metrics=evaluate(side); log.append({'side':side,'parameter':f'finger{i}_joint{joint+1}','value':value,'loss':loss})
                if loss<best: best=loss; selected=value
            state['finger_angles'][side][str(i)][joint]=selected
    for component,values in [(1,[.018,.028,.038]),(2,[-.014,-.004,.012])]:
        old=state['thumb_offsets'][side][component]; selected=old
        for value in values:
            state['thumb_offsets'][side][component]=value
            loss,metrics=evaluate(side); log.append({'side':side,'parameter':f'thumb_offset{component}','value':value,'loss':loss})
            if loss<best: best=loss; selected=value
        state['thumb_offsets'][side][component]=selected
    final_loss,metrics=evaluate(side)
    target=Vector((-.08 if side=='R' else .08,-.29,1.12))
    for name,offset in [('front',(.30,-1,.15)),('side',(1,0,.1)),('palm-side',(-.5,-.8,-.08))]:
        camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(QA/(side+'-'+name+'.png')); bpy.ops.render.render(write_still=True)
    render_views(QA/side)
    (QA/(side+'-metrics.json')).write_text(json.dumps({'before_loss':baseline_loss,'before':baseline,'after_loss':final_loss,'after':metrics,'grip_offsets':chosen,'finger_angles':state['finger_angles'][side],'thumb_offsets':state['thumb_offsets'][side],'art_accepted':False},indent=2)+'\n',encoding='utf-8')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); rig['state_json']=json.dumps(state)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_contact_calibrated.blend'))
report={'trial':'v002','stage':'bounded contact calibration dependency','maximum_evaluations':160,'evaluations':evaluations,'original_clock_preserved':True,'optimization_metric_is_not_art_pass':True,'search_log':log,'state':state,'source_sha256':artifact['sha256'],'artifact':{'path':(OUT/'ro_contact_calibrated.blend').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((OUT/'ro_contact_calibrated.blend').read_bytes()).hexdigest()},'rig_accepted':False,'animation_accepted':False}
(QA/'calibration.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_CONTACT_CALIBRATION '+json.dumps({'evaluations':evaluations,'master':report['artifact'],'acceptance':False}))
