"""v002 minimal rig tests before full skill poses. No animation or art PASS."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera,render_views
from ro_core_rig import assign,proximity,curl_digits,pose
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v002-rig-minimal'
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-rig-minimal'
fit=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-fit/fit.json').read_text())
artifact=next(a for a in fit['artifacts'] if a['path'].endswith('.blend'))
source=ROOT/artifact['path']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if OUT.exists() or QA.exists() or sha(source)!=artifact['sha256']: raise RuntimeError('Preserve sources/previous minimal rig')
phase=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-start.json').read_text())
now=datetime.now(timezone.utc)
if (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds'] or (now-datetime.fromisoformat(start['started_utc'])).total_seconds()>=phase['budget']['trial_seconds']: raise RuntimeError('Original budget exhausted')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
core=bpy.data.objects['SM_RO_core']; char=bpy.data.collections['COL_Character']
rest={'root':((0,0,0),(0,0,.18)),'pelvis':((0,.04,.89),(0,.04,1.0)),
      'spine_01':((0,.04,1.0),(0,.04,1.16)),'spine_02':((0,.04,1.16),(0,.06,1.34)),
      'neck':((0,.06,1.34),(0,.04,1.46)),'head':((0,.04,1.46),(0,.04,1.69))}
parents={'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
digits=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/core-landmark-probe/digits.json').read_text())
frames={}; grips={}; measurements={}
for side,sign in [('R',-1),('L',1)]:
    marks=fit['landmarks'][side]; shoulder=Vector(marks['shoulder']); elbow=Vector(marks['elbow']); wrist=Vector(marks['wrist'])
    groups=digits[side]['distal_groups']
    if len(groups)!=4: raise RuntimeError('Expected actual four distal branches')
    heads=[]; tips=[]
    for i,g in enumerate(groups,1):
        tip=Vector(g['tip']); cut=Vector(g['cut_center'])
        predicted=cut+(cut-tip)*((.866-cut.z)/(cut.z-tip.z))
        pts=[v.co for v in core.data.vertices if abs(v.co.z-.866)<.007 and abs(v.co.x-predicted.x)<.0135 and abs(v.co.y-predicted.y)<.032]
        if len(pts)<3: raise RuntimeError('Insufficient knuckle section')
        head=Vector([(min(p[j] for p in pts)+max(p[j] for p in pts))/2 for j in range(3)])
        head.z=.867; mid=head.lerp(tip,.52)
        # Use actual local middle section, not a single distal cut sample.
        pts=[v.co for v in core.data.vertices if abs(v.co.z-mid.z)<.006 and abs(v.co.x-mid.x)<.014 and abs(v.co.y-mid.y)<.025]
        if pts:
            mid=Vector([(min(p[j] for p in pts)+max(p[j] for p in pts))/2 for j in range(3)])
        a,b=f'finger{i}.{side}_01',f'finger{i}.{side}_02'
        rest[a]=(tuple(head),tuple(mid)); rest[b]=(tuple(mid),tuple(tip)); parents[a]='hand.'+side; parents[b]=a
        heads.append(head); tips.append(tip)
    palm=sum(heads,Vector())/4
    down=(palm-wrist).normalized()
    width=heads[-1]-heads[0]
    if width.x<0: width=-width
    width=(width-down*width.dot(down)).normalized()
    front=down.cross(width).normalized()
    if front.y>0: raise RuntimeError('Palm normal points away from visible palm')
    frame=Matrix((width,front,down)).transposed()
    if abs(frame.determinant()-1)>1e-6 or max(abs(frame.col[i].dot(frame.col[j])) for i in range(3) for j in range(i+1,3))>1e-6: raise RuntimeError('Palm frame not right-handed/orthogonal')
    frames[side]={'width':list(width),'front':list(front),'down':list(down),'determinant':frame.determinant()}
    grips[side]=list(palm+front*.033+down*.021)
    rest['hand.'+side]=(tuple(wrist),tuple(wrist+down*.082)); parents['hand.'+side]='lower_arm.'+side
    for name,h,t,parent in [('clavicle',(0,.06,1.33),shoulder,'spine_02'),('upper_arm',shoulder,elbow,'clavicle.'+side),('lower_arm',elbow,wrist,'upper_arm.'+side),
        ('upper_leg',(sign*.145,.05,.89),(sign*.177,.06,.50),'pelvis'),('lower_leg',(sign*.177,.06,.50),(sign*.195,.075,.105),'upper_leg.'+side),
        ('foot',(sign*.195,.075,.105),(sign*.195,-.11,.053),'lower_leg.'+side),('toe',(sign*.195,-.11,.053),(sign*.195,-.22,.053),'foot.'+side),
        ('pauldron',shoulder,shoulder+Vector((sign*.05,0,-.10)),'clavicle.'+side),('coat',(sign*.14,.06,.91),(sign*.27,.10,.46),'pelvis')]:
        rest[name+'.'+side]=(tuple(h),tuple(t)); parents[name+'.'+side]=parent
    rest['thumb.'+side+'_01']=((sign*.455,-.037,.914),(sign*.485,-.072,.894))
    outer=[Vector(p) for p in digits[side]['outer_thumb_points']]; thumb_tip=sum(outer,Vector())/len(outer)
    rest['thumb.'+side+'_02']=(rest['thumb.'+side+'_01'][1],tuple(thumb_tip))
    parents['thumb.'+side+'_01']='hand.'+side; parents['thumb.'+side+'_02']='thumb.'+side+'_01'
    measurements[side]={'knuckles':[list(x) for x in heads],'tips':[list(x) for x in tips],'thumb_tip':list(thumb_tip),'thumb_base_method':'manual center selected from actual palm/side closeups; not distal tip extrapolation'}
rest['tabard']=((0,-.13,.91),(0,-.18,.46)); parents['tabard']='pelvis'
width=Vector(frames['R']['width']); grip=Vector(grips['R'])
rest['sword']=(tuple(grip),tuple(grip-width*.8)); parents['sword']='hand.R'
# Creation order is parent-before-child, including digit branches.
ordered={}
while len(ordered)<len(rest):
    for n in rest:
        if n not in ordered and (parents[n] is None or parents[n] in ordered): ordered[n]=rest[n]
rest=ordered
data=bpy.data.armatures.new('RO_Core_Measured'); rig=bpy.data.objects.new('ARM_RO_Swordsman',data); char.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
gear_bones={n for n in rest if n.startswith(('coat.','pauldron.')) or n in {'sword','tabard'}}
for n,(h,t) in rest.items():
    bone=data.edit_bones.new(n); bone.head=h; bone.tail=t
    if parents[n]: bone.parent=data.edit_bones[parents[n]]
    if n=='root' or n in gear_bones: bone.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT'); rig.show_in_front=True
bpy.ops.object.select_all(action='DESELECT'); core.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active=rig
heat_warning=None
try: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except RuntimeError as e: heat_warning=str(e)
for n in gear_bones: data.bones[n].use_deform=True
modifier=next((m for m in core.modifiers if m.type=='ARMATURE'),None) or core.modifiers.new('Skin','ARMATURE'); modifier.object=rig; modifier.use_deform_preserve_volume=False
allowed={}
for v in core.data.vertices:
    x,y,z=v.co; side='L' if x>=0 else 'R'
    if z>1.46: names=['head']
    elif z<.35: names=['foot.'+side,'lower_leg.'+side] if z>.28 else ['foot.'+side]
    elif abs(x)>.34 and z<.96:
        names=['hand.'+side,'lower_arm.'+side]
        if z<.905:
            names=['hand.'+side]+[f'finger{i}.{side}_{j}' for i in range(1,5) for j in ('01','02')]+['thumb.'+side+'_01','thumb.'+side+'_02']
    elif z<.80: names=['pelvis','upper_leg.'+side,'lower_leg.'+side]
    elif abs(x)>.235 and z>.95: names=['clavicle.'+side,'upper_arm.'+side,'lower_arm.'+side,'hand.'+side,'spine_02']
    else:
        names=['pelvis','spine_01','spine_02','neck','head']
        if abs(x)>.11 and z>1.15: names+=['clavicle.'+side,'upper_arm.'+side]
    allowed[v.index]=set(names)
    existing={core.vertex_groups[g.group].name:g.weight for g in v.groups if core.vertex_groups[g.group].name in names and g.weight>1e-8}
    if z<.905 and abs(x)>.34: proximity(core,v,names,rest)
    elif existing: assign(core,v,existing)
    else: proximity(core,v,names,rest)
# One restrained graph smooth, filtered by each vertex's anatomical white list.
adj=[set() for v in core.data.vertices]
for edge in core.data.edges:
    a,b=edge.vertices; adj[a].add(b); adj[b].add(a)
for iteration in range(2):
    snapshot=[{core.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8} for v in core.data.vertices]
    for v in core.data.vertices:
        if len(allowed[v.index])==1 or not adj[v.index]: continue
        w={n:.75*value for n,value in snapshot[v.index].items()}
        for other in adj[v.index]:
            for n,value in snapshot[other].items():
                if n in allowed[v.index]: w[n]=w.get(n,0)+.25*value/len(adj[v.index])
        assign(core,v,w)
for ob in list(char.objects):
    if ob.type!='MESH' or ob==core: continue
    mod=ob.modifiers.new('Skin','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=False; ob.parent=rig
    if ob.name=='SM_RO_coat':
        for v in ob.data.vertices:
            amount=min(1,max(0,(.89-v.co.z)/.24)); side='L' if v.co.x>=0 else 'R'
            front=v.co.y<-.05 and abs(v.co.x)<.13
            assign(ob,v,{'pelvis':1-amount,'tabard' if front else 'coat.'+side:amount})
    else:
        n='spine_02' if 'cuirass' in ob.name else 'sword' if 'sword' in ob.name else ('pauldron.' if 'pauldron' in ob.name else 'lower_arm.')+ob.name[-1]
        for v in ob.data.vertices: assign(ob,v,{n:1})
sword=bpy.data.objects['SM_RO_sword']; old_grip=Vector((-.435,-.105,.86)); old_axis=Vector((-.2,-.6,-.775)).normalized()
rotation=old_axis.rotation_difference(-width).to_matrix()
for v in sword.data.vertices: v.co=grip+rotation@(v.co-old_grip)
sword.data.update()
state={'rest':rest,'parents':parents,'hand_frames':frames,'grips':grips,'measurements':measurements,'skin':'linear','weapon_axis_in_rest':list(-width)}
rig['state_json']=json.dumps(state); rig['control_method']='Editable FK with measured palm frames; geometric two-bone authoring, no IK/FK switch.'
OUT.mkdir(parents=True); QA.mkdir(parents=True)
scene=bpy.context.scene; render_views(QA/'bind')
def hands(folder):
    folder.mkdir(parents=True,exist_ok=True)
    for side in ['R','L']:
        target=rig.pose.bones['hand.'+side].head.lerp(rig.pose.bones['hand.'+side].tail,.65)
        camera((tuple(target+Vector((.25,-1,.15))),tuple(target),.27))
        scene.render.filepath=str(folder/(side+'.png')); bpy.ops.render.render(write_still=True)
hands(QA/'open-hands')
for side in ['R','L']: curl_digits(rig,state,side,.30)
hands(QA/'small-curl')
single=pose(rig,state,.89,(-.08,-.24,1.12),(0,-.1,.995),two_hands=False)
hands(QA/'single-grip'); render_views(QA/'single-grip')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_core_rig.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in char.objects: ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_core_rig.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True)
invalid=[]; illegal_core_gear=0
for ob in char.objects:
    if ob.type!='MESH': continue
    for v in ob.data.vertices:
        weights=[g.weight for g in v.groups if g.weight>1e-8]
        if not weights or len(weights)>4 or abs(sum(weights)-1)>1e-4: invalid.append([ob.name,v.index])
        if ob==core: illegal_core_gear+=sum(g.weight>1e-8 and ob.vertex_groups[g.group].name in gear_bones for g in v.groups)
report={'candidate':'v002','stage':'minimal rig direction and single-hand contact tests, no full skill poses yet','bones':len(data.bones),'triangles':58868,'heat_warning':heat_warning,'invalid_weights':invalid,'illegal_core_gear_influences':illegal_core_gear,'hand_frames':frames,'joint_measurements':measurements,'single_grip':single,'source_sha256':artifact['sha256'],'source_preserved':sha(source)==artifact['sha256'],'animation_channels':0,'art_accepted':False,'rig_accepted':False,'artifacts':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir()]}
(QA/'preflight.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_CORE_MINIMAL '+json.dumps({k:report[k] for k in ['bones','triangles','heat_warning','illegal_core_gear_influences','invalid_weights','single_grip']}))
