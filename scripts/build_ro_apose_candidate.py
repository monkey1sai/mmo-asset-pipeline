"""One source-preserving local trial: rig, semantic cloth weights and stress poses.

Preflight only. Does not declare acceptance or spend credits. Failed preflight
must be preserved and assessed before deciding whether full animation is useful.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import camera, render_views, material

out=ROOT/'assets/processed/ro-swordsman-combo-r003/v001'
qa=ROOT/'runs/qa/ro-swordsman-combo-r003/v001'
if out.exists() or qa.exists():
    raise ValueError('Preserve previous trial; cannot overwrite or reset')
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r003/v001-start.json').read_text(encoding='utf-8'))
ledger=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r003/quality-ledger.json').read_text(encoding='utf-8'))
assert ledger['trials'][0]['status']=='completed' and len(ledger['trials'])==1
source=ROOT/'assets/processed/ro-swordsman-combo-r003/baseline/ro_source_baseline.blend'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='6c459f248ee14e7a8e8f0db6ceedebeebde8804fe9b3c4bd59dd3e14c763b8b9'
out.mkdir(parents=True);qa.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene=bpy.context.scene
body=bpy.data.objects['SM_RO_APoseSource_0']
body.name='SM_RO_SourcePreservedBody'
char=bpy.data.collections.new('COL_Character');scene.collection.children.link(char)
for c in list(body.users_collection):c.objects.unlink(body)
char.objects.link(body)
# Diagnosed contact defects are at back neck and one belt seam. Keep surface UVs;
# do not seal arbitrary anatomical region cuts or remove source parts.
bm=bmesh.new();bm.from_mesh(body.data)
before_v=len(bm.verts)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
before_nm=sum(not e.is_manifold for e in bm.edges)
seen={};duplicates=[]
for face in bm.faces:
    key=frozenset(face.verts)
    if key in seen:duplicates.append(face)
    else:seen[key]=face
if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
after_nm=sum(not e.is_manifold for e in bm.edges)
bm.to_mesh(body.data);bm.free();body.data.update()

REST={'root':((0,0,0),(0,0,.18)), 'pelvis':((0,0,.88),(0,0,1.0)),
      'spine_01':((0,0,1.0),(0,0,1.16)), 'spine_02':((0,0,1.16),(0,0,1.34)),
      'neck':((0,0,1.34),(0,0,1.44)), 'head':((0,0,1.44),(0,0,1.68))}
PARENTS={'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
for side,s in [('L',1),('R',-1)]:
    for name,h,t,parent in [
        ('clavicle',(0,0,1.30),(s*.225,.015,1.30),'spine_02'),
        ('upper_arm',(s*.225,.015,1.30),(s*.342,-.012,1.102),'clavicle.'+side),
        ('lower_arm',(s*.342,-.012,1.102),(s*.431,-.067,.926),'upper_arm.'+side),
        ('hand',(s*.431,-.067,.926),(s*.462,-.067,.842),'lower_arm.'+side),
        ('upper_leg',(s*.16,0,.89),(s*.185,0,.50),'pelvis'),
        ('lower_leg',(s*.185,0,.50),(s*.195,0,.10),'upper_leg.'+side),
        ('foot',(s*.195,0,.10),(s*.195,-.12,.055),'lower_leg.'+side),
        ('toe',(s*.195,-.12,.055),(s*.195,-.22,.055),'foot.'+side),
        ('coat',(s*.14,.055,.86),(s*.27,.11,.40),'pelvis')]:
        REST[name+'.'+side]=(h,t);PARENTS[name+'.'+side]=parent
    for index,y in enumerate([-.128,-.094,-.060,-.026]):
        h=(s*.470,y,.829);mid=(s*.480,y,.790);tip=(s*.478,y,.758+abs(index-1)*.008)
        name='finger'+str(index+1)+'.'+side
        REST[name+'_01']=(h,mid);PARENTS[name+'_01']='hand.'+side
        REST[name+'_02']=(mid,tip);PARENTS[name+'_02']=name+'_01'
    REST['thumb.'+side+'_01']=((s*.409,-.080,.868),(s*.398,-.084,.834));PARENTS['thumb.'+side+'_01']='hand.'+side
    REST['thumb.'+side+'_02']=((s*.398,-.084,.834),(s*.391,-.087,.807));PARENTS['thumb.'+side+'_02']='thumb.'+side+'_01'
REST['tabard']=((0,-.12,.87),(0,-.15,.46));PARENTS['tabard']='pelvis'
REST['sword']=((-.445,-.08,.827),(-.445,-1.03,.827));PARENTS['sword']='hand.R'
arm=bpy.data.armatures.new('RO_APoseHumanoid')
rig=bpy.data.objects.new('ARM_RO_Swordsman',arm);char.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,(h,t) in REST.items():
    bone=arm.edit_bones.new(name);bone.head=h;bone.tail=t
    if PARENTS[name]:bone.parent=arm.edit_bones[PARENTS[name]]
    if name in {'root','sword'}:bone.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True

# Native Blender bone-heat is an initial weight proposal, never an art pass.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
heat_warning=None
try:bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except RuntimeError:heat_warning='Native bone-heat reported failure; semantic fallback must be independently inspected.'
mod=next((m for m in body.modifiers if m.type=='ARMATURE'),None)
if mod is None:mod=body.modifiers.new('Skin','ARMATURE');mod.object=rig
mod.use_deform_preserve_volume=False # Keep Blender and GLB on the same linear skinning.
body.parent=rig

def assign(vertex, weights):
    for group in body.vertex_groups:group.remove([vertex.index])
    weights={n:w for n,w in weights.items() if w>1e-8}
    total=sum(weights.values())
    for name,w in weights.items():
        group=body.vertex_groups.get(name) or body.vertex_groups.new(name=name)
        group.add([vertex.index],w/total,'REPLACE')

def dist_segment(p,name):
    h,t=map(Vector,REST[name]);d=t-h;q=max(0,min(1,(p-h).dot(d)/d.length_squared))
    return (p-h-d*q).length

# Sample the actual source UV atlas for cloth semantic masks; do not infer a
# coat from only a coordinate box or substitute new primitive anatomy.
image=bpy.data.images['texture_diffuse'];pixels=list(image.pixels);width,height=image.size
uv=body.data.uv_layers.active.data
colors={}
for poly in body.data.polygons:
    center=sum((uv[i].uv for i in poly.loop_indices),Vector((0,0)))/len(poly.loop_indices)
    px=min(width-1,max(0,int(center.x*width)));py=min(height-1,max(0,int(center.y*height)))
    c=pixels[(py*width+px)*4:(py*width+px)*4+3]
    for index in poly.vertices:colors.setdefault(index,[]).append(c)
counts={};unweighted=[]
for v in body.data.vertices:
    x,y,z=v.co;side='L' if x>=0 else 'R'
    samples=colors.get(v.index,[(.1,.1,.1)])
    c=[sum(row[i] for row in samples)/len(samples) for i in range(3)]
    blue=c[2]>c[0]*1.20 and c[2]>c[1]*1.03
    light=min(c)>.45 and max(c)-min(c)<.25
    semantic=None
    if .36<z<.85 and blue:semantic='coat.'+side
    elif .40<z<.84 and light and y<-.08 and abs(x)<.13:semantic='tabard'
    elif z>1.43:semantic='head'
    elif z<.37:semantic='foot.'+side # Whole boot remains rigid; preserve ground contact.
    elif .80<z<.96 and abs(x)<.23:semantic='pelvis'
    if semantic:
        assign(v,{semantic:1});counts[semantic]=counts.get(semantic,0)+1
    elif not any(g.weight>1e-8 for g in v.groups):
        names=['upper_arm.'+side,'lower_arm.'+side,'hand.'+side] if abs(x)>.23 and z>.79 else ['pelvis','spine_01','spine_02','neck'] if z>.87 else ['upper_leg.'+side,'lower_leg.'+side]
        distances=[(n,dist_segment(v.co,n)) for n in names]
        best=sorted(distances,key=lambda row:row[1])[:2]
        assign(v,{n:1/max(d,.02)**4 for n,d in best});unweighted.append(v.index)
    else:
        groups=[(body.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>1e-8 and body.vertex_groups[g.group].name in REST]
        groups=sorted(groups,key=lambda row:-row[1])[:4]
        assign(v,dict(groups))
for mat in body.data.materials:
    if not mat or not mat.use_nodes:continue
    for node in mat.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.30
    # Clamp roughness to tame the diagnosed patchy plate highlights; retain maps.
    bs=mat.node_tree.nodes.get('Principled BSDF')
    links=list(bs.inputs['Roughness'].links)
    if links:
        old=links[0].from_socket;mat.node_tree.links.remove(links[0])
        clamp=mat.node_tree.nodes.new('ShaderNodeMath');clamp.operation='MAXIMUM';clamp.inputs[1].default_value=.38
        mat.node_tree.links.new(old,clamp.inputs[0]);mat.node_tree.links.new(clamp.outputs[0],bs.inputs['Roughness'])

# Separate sword geometry, grip at the actual authored hand plane.
steel=material('SwordSteel',(.50,.58,.64),.82,.30)
gold=material('SwordBrass',(.42,.24,.07),.72,.36)
leather=material('SwordLeather',(.11,.05,.02),rough=.62)
def weapon_mesh(name, verts, faces, mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);char.objects.link(ob);data.materials.append(mat)
    group=ob.vertex_groups.new(name='sword');group.add(list(range(len(verts))),1,'REPLACE')
    skin=ob.modifiers.new('Skin','ARMATURE');skin.object=rig;ob.parent=rig
    return ob
grip=Vector(REST['sword'][0]);direction=Vector((0,-1,0));u=Vector((1,0,0));w=Vector((0,0,1))
def cylinder(name,start,end,radius,mat,segments=16):
    start,end=Vector(start),Vector(end);d=(end-start).normalized();a=d.cross(Vector((0,0,1)))
    if a.length<.01:a=d.cross(Vector((1,0,0)))
    a.normalize();b=d.cross(a);verts=[]
    for c in [start,end]:
        verts.extend(c+radius*(a*math.cos(i*math.tau/segments)+b*math.sin(i*math.tau/segments)) for i in range(segments))
    faces=[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    faces += [tuple(reversed(range(segments))),tuple(range(segments,2*segments))]
    return weapon_mesh(name,verts,faces,mat)
cylinder('SM_SwordGrip',grip-direction*.065,grip+direction*.060,.015,leather)
cylinder('SM_SwordPommel',grip-direction*.078,grip-direction*.058,.022,gold)
cylinder('SM_SwordGuard',grip+direction*.075-u*.085,grip+direction*.075+u*.085,.012,gold)
verts=[]
for d,width in [(.088,.025),(.65,.022),(.90,.001)]:
    c=grip+direction*d;verts.extend([c-u*width,c-w*.006,c+u*width,c+w*.006])
faces=[(j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i) for j in range(2) for i in range(4)]+[(3,2,1,0),(8,9,10,11)]
weapon_mesh('SM_SwordBlade',verts,faces,steel)
arm.bones['sword'].use_deform=True

def solve(head,target,l1,l2,pole):
    head,target,pole=map(Vector,(head,target,pole));delta=target-head
    distance=min(l1+l2-.0005,max(abs(l1-l2)+.0005,delta.length));direction=delta.normalized();target=head+direction*distance
    bend=pole-direction*pole.dot(direction);bend.normalize()
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    return head+direction*along+bend*math.sqrt(max(0,l1*l1-along*along)),target

def matrix(head,tail,reference):
    axis=(Vector(tail)-Vector(head)).normalized();x=axis.cross(reference)
    if x.length<1e-6:x=axis.cross(Vector((1,0,0)))
    x.normalize();z=x.cross(axis).normalized();m=Matrix((x,axis,z)).transposed().to_4x4();m.translation=head
    return m

def pose(frame,hip_height,rh,lh,sword_dir,yaw=0):
    scene.frame_set(frame);body.data.update()
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    hip=Vector((0,0,hip_height));yawmat=Matrix.Rotation(yaw,3,'Z')
    shift=hip-Vector(REST['pelvis'][0])
    worlds={}
    for name in ['root','pelvis','spine_01','spine_02','neck','head']:
        bone=arm.bones[name];m=bone.matrix_local.copy()
        if name!='root':m.translation+=shift
        worlds[name]=m
    for side,s,target in [('L',1,lh),('R',-1,rh)]:
        shoulder=Vector(REST['upper_arm.'+side][0])+shift
        l1=(Vector(REST['upper_arm.'+side][1])-Vector(REST['upper_arm.'+side][0])).length
        l2=(Vector(REST['lower_arm.'+side][1])-Vector(REST['lower_arm.'+side][0])).length
        elbow,wrist=solve(shoulder,target,l1,l2,(s*.2,1,.2))
        worlds['clavicle.'+side]=arm.bones['clavicle.'+side].matrix_local.copy();worlds['clavicle.'+side].translation+=shift
        worlds['upper_arm.'+side]=matrix(shoulder,elbow,arm.bones['upper_arm.'+side].matrix_local.to_3x3().col[2])
        worlds['lower_arm.'+side]=matrix(elbow,wrist,arm.bones['lower_arm.'+side].matrix_local.to_3x3().col[2])
        direction=Vector(sword_dir).normalized() if side=='R' else Vector((0,0,-1))
        # Stable hand frame, based on actual rest axis; independent of a hard sign flip.
        handaxis=Vector((s*.3,-.1,-.95)).normalized()
        worlds['hand.'+side]=matrix(wrist,wrist+handaxis*.09,Vector((0,1,0)))
        thigh=Vector(REST['upper_leg.'+side][0])+shift
        ankle=Vector(REST['lower_leg.'+side][1])
        knee,unused=solve(thigh,ankle,(Vector(REST['upper_leg.'+side][1])-Vector(REST['upper_leg.'+side][0])).length,
                          (Vector(REST['lower_leg.'+side][1])-Vector(REST['lower_leg.'+side][0])).length,(0,-1,0))
        worlds['upper_leg.'+side]=matrix(thigh,knee,arm.bones['upper_leg.'+side].matrix_local.to_3x3().col[2])
        worlds['lower_leg.'+side]=matrix(knee,ankle,arm.bones['lower_leg.'+side].matrix_local.to_3x3().col[2])
        for name in ['foot.'+side,'toe.'+side]:worlds[name]=arm.bones[name].matrix_local.copy()
        name='coat.'+side;worlds[name]=arm.bones[name].matrix_local.copy();worlds[name].translation+=shift
    worlds['tabard']=arm.bones['tabard'].matrix_local.copy();worlds['tabard'].translation+=shift
    for name in REST:
        if name not in worlds:continue
        pb=rig.pose.bones[name];rest=arm.bones[name].matrix_local;parent=PARENTS[name]
        pb.matrix_basis=rest.inverted()@arm.bones[parent].matrix_local@worlds[parent].inverted()@worlds[name] if parent else rest.inverted()@worlds[name]
    bpy.context.view_layer.update()
    for side,s in [('L',1),('R',-1)]:
        for index in range(1,5):
            for joint,angle in [('_01',.62),('_02',.95)]:
                pb=rig.pose.bones['finger'+str(index)+'.'+side+joint]
                rest=arm.bones[pb.name].matrix_local.to_3x3()
                pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation(s*angle,3,'Y')@rest).to_quaternion()
    bpy.context.view_layer.update()
    hand=rig.pose.bones['hand.R'].matrix
    relative=arm.bones['hand.R'].matrix_local.inverted()@Vector(REST['sword'][0])
    location=hand@relative
    rig.pose.bones['sword'].matrix=matrix(location,location+Vector(sword_dir).normalized()*.95,Vector((0,1,0)))
    bpy.context.view_layer.update()

# Rest visual comparison plus three real deformation stress poses, no VFX.
rig.data.pose_position='REST';render_views(qa/'bind');rig.data.pose_position='POSE'
poses=[('overhead',.88,(-.20,-.12,1.61),(.17,-.12,1.57),(0,-.2,.98)),
       ('deep-crouch',.68,(-.20,-.32,.98),(.19,-.28,1.0),(-.1,-.65,.75)),
       ('downslash',.78,(-.16,-.40,.90),(.18,-.30,1.05),(0,-.8,-.6))]
scene.render.resolution_x=scene.render.resolution_y=960
for frame,(name,h,rh,lh,sd) in enumerate(poses,1):
    pose(frame,h,rh,lh,sd)
    folder=qa/'preflight'/name;folder.mkdir(parents=True)
    for view in ['front','side','back','three-quarter']:
        camera(view);scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
pose(1,.88,(-.28,-.20,1.08),(.18,-.19,1.10),(-.3,-.1,.95))
render_views(qa)
scene.frame_set(1);camera();bpy.ops.wm.save_as_mainfile(filepath=str(out/'ro_swordsman_preflight.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in char.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(out/'ro_swordsman_preflight.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_skins=True)
report={'trial':'v001','same_started_utc':start['started_utc'],'source_baseline_sha256':ledger['trials'][0]['evidence']['subject_artifacts'][0]['sha256'],
        'source_vertices_before':before_v,'source_vertices_after':len(body.data.vertices),'duplicate_faces_removed':len(duplicates),
        'nonmanifold_before':before_nm,'nonmanifold_after':after_nm,'bone_heat_warning':heat_warning,'semantic_weights':counts,
        'fallback_unweighted_vertices':len(unweighted),'bones':len(arm.bones),'linear_skinning':True,
        'triangles':sum(len(f.vertices)-2 for ob in char.objects if ob.type=='MESH' for f in ob.data.polygons),
        'stress_poses':[x[0] for x in poses],'animation':False,'effects':False,'acceptance':'Not run; preserve preflight and inspect before full sequence.',
        'artifacts':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.suffix in {'.blend','.glb'}}}
(qa/'preflight-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('APOSE_PREFLIGHT '+json.dumps(report))
