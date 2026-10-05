"""Fixed-joint small-motion skin diagnosis; UV remains failed and unrebaked."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
import bpy
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign
from ro_hand_gate import segment_hit
from ro_review_common import camera,material
BASE=ROOT/'runs/qa/ro-swordsman-combo-r007';QA=BASE/'v003-skin-diagnostic';OUT=ROOT/'assets/processed/ro-swordsman-combo-r007/v003-skin-diagnostic'
start=json.loads((BASE/'v003-start.json').read_text());clock=json.loads((BASE/'phase-start.json').read_text())
patch=json.loads((BASE/'v003-thumb-patch/patch.json').read_text());probe=json.loads((ROOT/start['joint_probe']['path']).read_text())
assert patch['geometry']['source_gate'];source=ROOT/patch['artifact']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==patch['artifact']['sha256']
assert not QA.exists() and not OUT.exists();QA.mkdir();OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];ob.data.update();ob.data.calc_loop_triangles()
rest_points=[v.co.copy() for v in ob.data.vertices];rest_edges=[tuple(e.vertices) for e in ob.data.edges]
landmarks={name:[Vector(p) for p in values] for name,values in probe['scaled_landmarks'].items()}
wrist=Vector(probe['wrist_center_scaled']);front=Vector((0,-1,0))
arm=bpy.data.armatures.new('HandDiagnosticArmature');rig=bpy.data.objects.new('ARM_RO_HandDiagnostic',arm)
bpy.context.scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
hand=arm.edit_bones.new('hand');hand.head=wrist;hand.tail=wrist+Vector((0,0,.050))
for branch,points in landmarks.items():
    parent=hand
    for i,(h,t) in enumerate(zip(points,points[1:]),1):
        b=arm.edit_bones.new(f'{branch}_{i:02}');b.head=h;b.tail=t;b.parent=parent;b.use_connect=i>1;parent=b
bpy.ops.object.mode_set(mode='OBJECT')
def segment_parameter(p,points):
    lengths=[(b-a).length for a,b in zip(points,points[1:])];rows=[];total=0
    for i,(a,b,length) in enumerate(zip(points,points[1:],lengths)):
        d=(b-a)/length;s=(p-a).dot(d);clamped=max(0,min(length,s))
        rows.append(((p-a-d*clamped).length,total+(s if i==0 and s<0 else clamped)))
        total+=length
    return min(rows,key=lambda x:x[0]),lengths
def smooth(value):
    t=max(0,min(1,value));return t*t*(3-2*t)
semantic={};pads={name:[] for name in landmarks};weights_record={};cap_vertices=[]
scale=json.loads((BASE/'v001-source-preparation/preparation.json').read_text())['uniform_scale']
for v,p in zip(ob.data.vertices,rest_points):
    distances={name:segment_parameter(p,points) for name,points in landmarks.items()}
    branch=None
    if p.z>.170*scale:branch=min(distances,key=lambda n:distances[n][0][0])
    elif p.z>.118*scale and p.x>.011*scale and distances['thumb'][0][0]<.036*scale:branch='thumb'
    weights={'hand':1.}
    if branch:
        (radial,s),lengths=distances[branch]
        root_blend=smooth((s+.008)/.016)
        if branch=='thumb':
            root_blend*=smooth((.036*scale-radial)/(.012*scale))
        # Adjacent smooth weight zones remain well proximal of the distal cap.
        widths=[.0045,.0040]
        j1=smooth((s-lengths[0]+widths[0])/(2*widths[0]))
        j2=smooth((s-sum(lengths[:2])+widths[1])/(2*widths[1]))
        weights={'hand':1-root_blend,f'{branch}_01':root_blend*(1-j1),
            f'{branch}_02':root_blend*j1*(1-j2),f'{branch}_03':root_blend*j1*j2}
        semantic[v.index]={'branch':branch,'axial_m':s,'radial_m':radial}
        if s>.008 and s<sum(lengths)-.003 and v.normal.dot(front)>.2:pads[branch].append(v.index)
    assign(ob,v,weights)
    weights_record[v.index]={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
    if ob.data.attributes['r007_source_point_id'].data[v.index].value==0 and branch=='thumb':
        ip=landmarks['thumb'][2];d=(landmarks['thumb'][3]-ip).normalized()
        if (p-ip).dot(d)>.0095294:cap_vertices.append(v.index)
assert all(len(ids)>=3 for ids in pads.values()),pads
assert all(len(row)<=4 and abs(sum(row.values())-1)<1e-5 for row in weights_record.values())
assert all(all(n=='hand' or n.startswith(row['branch']+'_') for n in weights_record[i]) for i,row in semantic.items())
assert all(weights_record[i].get('thumb_03',0)>.99999 for i in cap_vertices)
mod=ob.modifiers.new('Skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False;ob.parent=rig
ob['fixed_pad_indices']=json.dumps(pads);ob['fixed_semantic']=json.dumps(semantic)
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(QA/'frozen-masks-and-weights.json',{'source':patch['artifact'],'joint_probe':start['joint_probe'],
    'semantic':semantic,'pads':pads,'weights':weights_record,'cap_rigid_vertices':cap_vertices,
    'maximum_influences':max(map(len,weights_record.values())),'normalized':True,'own_branch_only':True,
    'weight_blend_half_width_m':[.0045,.0040],'material_gate':'fail_cross_island16','joint_positions_unchanged':True})
def reset():
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def rotate(name,angle,opposition=0):
    pb=rig.pose.bones[name];native=rig.data.bones[name].matrix_local.to_3x3()
    direction=(rig.data.bones[name].tail_local-rig.data.bones[name].head_local).normalized()
    axis=front.cross(direction).normalized()
    rotation=Matrix.Rotation(-angle,3,axis)
    if opposition:rotation=Matrix.Rotation(-opposition,3,Vector((0,0,1)))@rotation
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(native.inverted()@rotation@native).to_quaternion()
    bpy.context.view_layer.update()
def actual(label,parameters):
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    assert [r.value for r in mesh.attributes['r007_original_point_id'].data]==list(range(len(rest_points)))
    points=[v.co.copy() for v in mesh.vertices];triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
    ev.to_mesh_clear();tree=BVHTree.FromPolygons(points,triangles,all_triangles=True);crossings=[]
    for i,j in tree.overlap(tree):
        if i>=j or set(triangles[i])&set(triangles[j]):continue
        a=[points[k] for k in triangles[i]];b=[points[k] for k in triangles[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(a,b),(b,a)] for k in range(3)):crossings.append([i,j])
    ratios=[{'edge':[a,b],'ratio':(points[b]-points[a]).length/(rest_points[b]-rest_points[a]).length} for a,b in rest_edges]
    degenerates=sum((points[b]-points[a]).cross(points[c]-points[a]).length<1e-12 for a,b,c in triangles)
    return {'label':label,'parameters':parameters,'observed_utc':now.isoformat(),'transverse_self_pairs':len(crossings),
        'crossings':crossings[:20],'degenerate_triangles':degenerates,
        'maximum_edge_stretch':max(r['ratio'] for r in ratios),'minimum_edge_ratio':min(r['ratio'] for r in ratios),
        'worst_stretch':sorted(ratios,key=lambda r:-r['ratio'])[:5],'worst_compression':sorted(ratios,key=lambda r:r['ratio'])[:5],
        'evaluated_fingerprint':hashlib.sha256(json.dumps({'points':[list(p) for p in points],'triangles':triangles,'parameters':parameters},sort_keys=True).encode()).hexdigest()},points
events=[];direction=[]
for name in ['thumb_03','thumb_02','thumb_01']:
    reset();base,neutral=actual('direction-baseline-'+name,{'bone':name,'angle':0});events.append(base)
    ids=[i for i,row in weights_record.items() if row.get(name,0)>.5]
    for angle in [-.05,.05]:
        reset();rotate(name,angle);row,pts=actual('direction-'+name,{'bone':name,'angle':angle});events.append(row)
        delta=sum((pts[i]-neutral[i] for i in ids),Vector())/len(ids)
        direction.append({'bone':name,'angle':angle,'mean_surface_displacement':list(delta),
            'toward_palm_m':delta.dot(front),'expected_direction_pass':delta.dot(front)*angle>0,'weighted_vertices':len(ids)})
reset();open_row,_=actual('open',{'angle':0});events.append(open_row)
def views(label):
    target=(.005,0,.18)
    for name,location in {'palm':(0,-1,.22),'side':(1,-.2,.24),'back':(0,1,.22)}.items():
        camera((location,target,.29));bpy.context.scene.render.filepath=str(QA/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
gray=material('SmallMotionGray',(.55,.55,.55));saved_materials=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(gray)
views('open')
for angle in [.15,.30]:
    reset()
    for branch in landmarks:
        for joint,factor in [(1,1),(2,1.4),(3,.85)]:rotate(f'{branch}_{joint:02}',angle*factor)
    row,_=actual('combined-small-'+str(angle),{'proximal_rad':angle,'joint_factors':[1,1.4,.85]});events.append(row);views('small-'+str(angle))
reset();ob.data.materials.clear()
for m in saved_materials:ob.data.materials.append(m)
artifact=OUT/'right_hand_small_motion.blend';bpy.ops.wm.save_as_mainfile(filepath=str(artifact))
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':patch['artifact'],'events':events,
    'direction':direction,'all_tested_thumb_curl_directions_pass':all(r['expected_direction_pass'] for r in direction),
    'small_motion_numeric_gate':all(not r['transverse_self_pairs'] and not r['degenerate_triangles'] for r in events),
    'joint_positions_unchanged':True,'thumb_bones':3,'cap_follows_distal_only':True,
    'material_gate':False,'material_reason':'16cross-islandfaces; retained as failed visual/material evidence; no rebake',
    'visual_deformation_acceptance':'pending actual rendered gray views','full_animation_accepted':False,
    'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
    'limitations':['Zero transverse count excludes adjacent folds and coplanar/tangential cases','Edge ratios diagnostic only','CMC opposition axis separate next test','No sword/contact/assembly test yet']}
save(QA/'skin.json',report)
print('RO_SMALL_MOTION '+json.dumps({'direction':report['all_tested_thumb_curl_directions_pass'],'numeric_gate':report['small_motion_numeric_gate'],'events':[(r['label'],r['transverse_self_pairs'],r['maximum_edge_stretch']) for r in events]}))
