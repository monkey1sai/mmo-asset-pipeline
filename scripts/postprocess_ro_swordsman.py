"""Last bounded candidate: retain generated surfaces, separate fused regions,
author a matched humanoid bind rig, and bake the reference skill sequence.
Produces a candidate for inspection, never an acceptance result.
"""
import argparse
import ast
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
parser=argparse.ArgumentParser()
parser.add_argument('--render-animation',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
started=time.monotonic()
OUT=ROOT/'assets/processed/ro-swordsman-combo/v004'
QA=ROOT/'runs/qa/ro-swordsman-combo/v004'
OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)
source=ROOT/'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb'
if hashlib.sha256(source.read_bytes()).hexdigest()!='9350ee0a6cbe9af02bedabcc7ccee01153b7af90edc7f604dae67d205999e4c1':
    raise RuntimeError('Source drift')
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
original=next(o for o in bpy.context.scene.objects if o.type=='MESH')
world=original.matrix_world.copy()
points=[world @ v.co for v in original.data.vertices]
low=Vector(tuple(min(v[i] for v in points) for i in range(3)))
high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
factor=1.74/(high.z-low.z); center=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
for v in original.data.vertices: v.co=(world @ v.co-center)*factor
original.parent=None; original.matrix_world=Matrix.Identity(4)
bm=bmesh.new(); bm.from_mesh(original.data)
before=len(bm.verts); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(original.data); bm.free()
for p in original.data.polygons:p.use_smooth=True
character=bpy.data.collections.new('COL_Character'); bpy.context.scene.collection.children.link(character)
stage=bpy.data.collections.new('COL_ReviewStage'); bpy.context.scene.collection.children.link(stage)
effects=bpy.data.collections.new('COL_SkillEffects'); bpy.context.scene.collection.children.link(effects)

def move_collection(o,col):
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o)

def material(name,color,metal=0,rough=.5,emission=0):
    m=bpy.data.materials.new('MAT_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m

M={'white':material('IvoryTabard',(.72,.69,.59),rough=.88),
   'seam':material('HiddenClothSeam',(.023,.035,.052),rough=.88),
   'edge':material('SwordSteel',(.57,.65,.72),.85,.25),
   'gold':material('SwordBrass',(.46,.25,.065),.72,.35),
   'leather':material('SwordLeather',(.095,.042,.019),rough=.6)}
for m in original.data.materials:
    if m and m.use_nodes:
        for node in m.node_tree.nodes:
            if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.35

REST={'root':((0,0,0),(0,0,.18)), 'pelvis':((0,0,.86),(0,0,.98)),
      'spine_01':((0,0,.98),(0,0,1.15)), 'spine_02':((0,0,1.15),(0,0,1.34)),
      'neck':((0,0,1.34),(0,0,1.43)), 'head':((0,0,1.43),(0,0,1.69))}
PARENTS={'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
for side,s in [('L',1),('R',-1)]:
    definitions={'clavicle':((0,0,1.30),(s*.24,0,1.30)),
      'upper_arm':((s*.24,0,1.30),(s*.29,-.005,1.06)),
      'lower_arm':((s*.29,-.005,1.06),(s*.16,-.165,.935)),
      'hand':((s*.16,-.165,.935),(s*.10,-.19,.872)),
      'upper_leg':((s*.12,0,.88),(s*.16,0,.47)),
      'lower_leg':((s*.16,0,.47),(s*.18,-.02,.09)),
      'foot':((s*.18,-.02,.09),(s*.18,-.16,.035)),
      'toe':((s*.18,-.16,.035),(s*.18,-.22,.035)),
      'coat':((s*.13,.025,.87),(s*.23,.04,.49))}
    for name,value in definitions.items():REST[name+'.'+side]=value
    for name,parent in [('clavicle','spine_02'),('upper_arm','clavicle.'+side),('lower_arm','upper_arm.'+side),('hand','lower_arm.'+side),('upper_leg','pelvis'),('lower_leg','upper_leg.'+side),('foot','lower_leg.'+side),('toe','foot.'+side),('coat','pelvis')]:PARENTS[name+'.'+side]=parent
REST['sword']=((-.12,-.20,.90),(-.12,-.20,1.85));PARENTS['sword']='hand.R'

def segment_distance(p,a,b):
    a,b=Vector(a),Vector(b);d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared))
    return (p-(a+d*t)).length,t

# Boundaries are recorded construction decisions. They require visual inspection;
# closed geometry and normalized weights alone cannot establish anatomy quality.
weapon_line=(Vector((.13,-.175,.88)),Vector((.43,-.12,.45)))
def region(p):
    x,y,z=p;side='L' if x>0 else 'R'
    sword_d,_=segment_distance(p,*weapon_line)
    if sword_d<.063 and .37<z<.86 and x>.12:return 'RemovedSourceWeapon'
    if -.035<x<.10 and y<-.145 and 1.01<z<1.14:return 'RemovedSourceHandle'
    if z>1.395:return 'Head'
    distances=[segment_distance(p,*REST[n+'.'+side])[0] for n in ['upper_arm','lower_arm','hand']]
    if .83<z<1.405 and min(distances)<.091 and (abs(x)>.205 or (y<-.133 and z<1.025 and abs(x)>.058)):
        return 'Arm.'+side
    if z<.885:
        if .44<z<.875 and (abs(x)>.235 or y>.052 or (y<-.08 and abs(x)>.14)):
            return 'Coat.'+side
        if .49<z<.87 and abs(x)<.14 and y<-.09:return 'Tabard'
        return 'Leg.'+side
    return 'Torso'

def cap_boundary_fans(bm,material_index):
    """Trace each boundary halfedge through its own incident face fan.

    holes_fill can create diagonals that already exist at a branching cut.
    Each traced boundary gets a fresh center; caps therefore add exactly one
    incident face per cut edge. This is hidden surface reconstruction, not
    proof of correct silhouette or absence of geometric self intersection.
    """
    boundary=[e for e in bm.edges if e.is_boundary]
    unvisited=set(boundary);cycles=[]
    while unvisited:
        start=next(iter(unvisited)).link_loops[0];current=start;cycle=[]
        for _ in range(len(boundary)+1):
            if current.edge not in unvisited:
                if current is not start:raise RuntimeError('Boundary fan merged unexpectedly')
                break
            unvisited.remove(current.edge);cycle.append(current.vert)
            current=current.link_loop_next
            guard=0
            while not current.edge.is_boundary:
                if len(current.edge.link_faces)!=2:raise RuntimeError('Precap nonmanifold fan')
                current=current.link_loop_radial_next.link_loop_next;guard+=1
                if guard>len(bm.faces):raise RuntimeError('Boundary traversal did not terminate')
            if current is start:break
        else:raise RuntimeError('Boundary cycle did not close')
        # Split a pinched cycle at repeated vertices, preserving all edges.
        pending=[cycle]
        while pending:
            vertices=pending.pop();seen={};split=False
            for i,v in enumerate(vertices):
                if v in seen:
                    j=seen[v];pending.extend([vertices[j:i],vertices[:j]+vertices[i:]]);split=True;break
                seen[v]=i
            if not split:
                if len(vertices)<3:raise RuntimeError('Degenerate boundary cycle')
                cycles.append(vertices)
    for vertices in cycles:
        center=bm.verts.new(sum((v.co for v in vertices),Vector())/len(vertices))
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            face=bm.faces.new((b,a,center));face.material_index=material_index
    return len(boundary),len(cycles)

labels={p.index:region(p.center) for p in original.data.polygons}
parts=[];topology=[]
for label in sorted(set(labels.values())):
    if label.startswith('Removed'):continue
    data=original.data.copy();ob=bpy.data.objects.new('SM_RO_'+label,data);character.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if labels[f.index]!=label],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    data.materials.append(M['seam']); seam_index=len(data.materials)-1
    boundary_count,cap_count=cap_boundary_fans(bm,seam_index)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    topology.append({'part':label,'vertices':len(bm.verts),'triangles':len(bm.faces),'cut_boundary_edges':boundary_count,'cap_cycles':cap_count,'nonmanifold':sum(not e.is_manifold for e in bm.edges)})
    bm.to_mesh(data);bm.free()
    if label=='Tabard':
        data.materials.clear();data.materials.append(M['white'])
        for p in data.polygons:p.material_index=0
    for p in data.polygons:p.use_smooth=True
    parts.append((ob,label))
bpy.data.objects.remove(original,do_unlink=True)
(QA/'topology-pre-rig.json').write_text(json.dumps({'method':'Exact seam weld, explicit region separation, hidden seam caps; source raw bytes preserved','vertices_before':before,'parts':topology,'manual_edge_loop_retopology':'not_done','visual_acceptance':'not_run'},indent=2),encoding='utf-8')

arm_data=bpy.data.armatures.new('RO_Humanoid_MatchedBind');rig=bpy.data.objects.new('ARM_RO_Swordsman',arm_data);character.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,(a,b) in REST.items():
    bone=arm_data.edit_bones.new(name);bone.head=a;bone.tail=b
    if PARENTS[name]:bone.parent=arm_data.edit_bones[PARENTS[name]]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True

def weighted(ob,weights):
    for v in ob.data.vertices:
        ws={k:w for k,w in weights(v.co).items() if w>1e-6}
        ws=dict(sorted(ws.items(),key=lambda x:-x[1])[:4]);total=sum(ws.values())
        if total<=0:raise ValueError('Unweighted vertex')
        for name,w in ws.items():
            group=ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name);group.add([v.index],w/total,'REPLACE')
    mod=ob.modifiers.new('Skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True;ob.parent=rig

def weights(label,p):
    if label=='Head':return {'head':1}
    if label=='Tabard':return {'pelvis':1}
    if label.startswith('Coat.'):return {'coat.'+label[-1]:1}
    if label.startswith('Arm.'):
        side=label[-1];names=[n+'.'+side for n in ['upper_arm','lower_arm','hand']]
        distances=[segment_distance(p,*REST[n])[0] for n in names]
        ws=[math.exp(-d*d/.0024) for d in distances]
        return dict(zip(names,ws))
    if label.startswith('Leg.'):
        side=label[-1]
        if p.z<.16:return {'foot.'+side:1}
        t=max(0,min(1,(p.z-.415)/.11))
        if p.z>.8:
            h=max(0,min(.65,(p.z-.80)/.12));return {'upper_leg.'+side:1-h,'pelvis':h}
        return {'upper_leg.'+side:t,'lower_leg.'+side:1-t}
    t=max(0,min(1,(p.z-1.04)/.15))
    if p.z<1.04:return {'pelvis':max(0,(1.04-p.z)/.13),'spine_01':min(1,(p.z-.91)/.13)}
    if p.z>1.33:return {'neck':min(1,(p.z-1.33)/.08),'spine_02':max(0,1-(p.z-1.33)/.08)}
    return {'spine_01':1-t,'spine_02':t}
for ob,label in parts:weighted(ob,lambda p,label=label:weights(label,p))

def mesh(name,vs,fs,mat,bone):
    data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update()
    ob=bpy.data.objects.new('SM_'+name,data);character.objects.link(ob);data.materials.append(M[mat]);weighted(ob,lambda p:{bone:1});return ob

def cylinder(name,a,b,r,mat,bone,n=16):
    a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,1,0))).normalized();v=d.cross(u)
    vs=[tuple(c+r*(u*math.cos(j*math.tau/n)+v*math.sin(j*math.tau/n))) for c in (a,b) for j in range(n)]
    fs=[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]+[tuple(reversed(range(n))),tuple(range(n,2*n))]
    return mesh(name,vs,fs,mat,bone)

sx,sy,sz=REST['sword'][0]
cylinder('SwordGrip',(sx,sy,sz-.055),(sx,sy,sz+.065),.015,'leather','sword')
cylinder('SwordGuard',(sx-.095,sy,sz+.074),(sx+.095,sy,sz+.074),.014,'gold','sword')
cylinder('SwordPommel',(sx,sy,sz-.07),(sx,sy,sz-.052),.023,'gold','sword')
vs=[]
for z,w in [(sz+.09,.027),(sz+.69,.021),(sz+.93,.0003)]:vs.extend([(sx-w,sy,z),(sx,sy-.005,z),(sx+w,sy,z),(sx,sy+.005,z)])
fs=[(k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j) for k in range(2) for j in range(4)]+[(3,2,1,0),(8,9,10,11)]
mesh('SwordBlade',vs,fs,'edge','sword')
cylinder('Scabbard',(.19,.09,.90),(.34,.10,.31),.032,'leather','pelvis')

# Reuse only the inspected reference pose constants and two mathematical helpers;
# do not execute the earlier construction pipeline or import its scene mutations.
tree=ast.parse((ROOT/'scripts/build_ro_swordsman.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in {'solve','bone_matrix'}) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POSES' for t in n.targets))]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<inspected pose helpers>','exec'),globals())
POSES=[list(p) for p in POSES]
for p in POSES:
    if p[0] not in (75,100):p[1]=min(.86,p[1]-.035)
    for idx in (7,8):
        point=list(p[idx]);point[2]-=.04;p[idx]=tuple(point)
    if p[0]==100:p[4]=(-.15,-.12,1.62);p[6]=(-.06,-.13,1.56)
    if p[0] in (280,300):p[4]=(-.18,-.16,.94);p[6]=(.16,-.16,.94)

metrics=[]
def set_pose(f,p):
    _,hz,lean,yaw,rh,sd,lh,lf,rf=p;ym=Matrix.Rotation(yaw,3,'Z')
    def world(v):return ym @ Vector(v)
    hip=Vector((0,0,hz));sp1=hip+world((0,0,.12));sp2=sp1+world((0,lean*.38,.17));neck=sp2+world((0,lean*.40,.19));head=neck+world((0,0,.09))
    lm={'root':(Vector((0,0,0)),Vector((0,0,.18))),'pelvis':(hip,sp1),'spine_01':(sp1,sp2),'spine_02':(sp2,neck),'neck':(neck,head),'head':(head,head+world((0,0,.26)))}
    for side,s,ht,ft in [('L',1,lh,lf),('R',-1,rh,rf)]:
        shoulder=neck+world((s*.24,0,-.04))
        lengths=[(Vector(REST[n+'.'+side][1])-Vector(REST[n+'.'+side][0])).length for n in ['upper_arm','lower_arm','upper_leg','lower_leg']]
        elbow,wrist=solve(shoulder,world(ht),lengths[0],lengths[1],world((s,1,-.3)))
        handdir=world(sd).normalized() if side=='R' else world((-.2,0,-1)).normalized()
        if side=='L' and 35<f<135:handdir=world(sd).normalized()
        handtail=wrist+handdir*(Vector(REST['hand.'+side][1])-Vector(REST['hand.'+side][0])).length
        th=hip+world((s*.12,0,.02));knee,ankle=solve(th,Vector(ft),lengths[2],lengths[3],Vector((0,-1,0)))
        toe=ankle+world((0,-.14,-.055))
        lm.update({'clavicle.'+side:(neck+world((0,0,-.04)),shoulder),'upper_arm.'+side:(shoulder,elbow),'lower_arm.'+side:(elbow,wrist),'hand.'+side:(wrist,handtail),'upper_leg.'+side:(th,knee),'lower_leg.'+side:(knee,ankle),'foot.'+side:(ankle,toe),'toe.'+side:(toe,toe+world((0,-.06,0))),'coat.'+side:(hip+world((s*.13,.025,.01)),hip+world((s*(.23+.025*math.sin(f*.055)),.04+.018*math.sin(f*.08),-.37)))})
    sdworld=world(sd).normalized();grip=lm['hand.R'][0]+sdworld*.055
    lm['sword']=(grip,grip+sdworld*.95)
    matrices={}
    for name,(a,b) in lm.items():
        reference=world(arm_data.bones[name].matrix_local.to_3x3().col[2]);matrix=bone_matrix(a,b,reference);matrix.translation=a
        pb=rig.pose.bones[name];parent=PARENTS[name];rest=arm_data.bones[name].matrix_local
        pb.matrix_basis=rest.inverted() @ arm_data.bones[parent].matrix_local @ matrices[parent].inverted() @ matrix if parent else rest.inverted() @ matrix
        matrices[name]=matrix;pb.rotation_mode='QUATERNION';pb.keyframe_insert('location',frame=f,group=name);pb.keyframe_insert('rotation_quaternion',frame=f,group=name)
    metrics.append({'frame':f,'right_grip_distance_m':(grip-(lm['hand.R'][0]+sdworld*.055)).length,'left_wrist_to_grip_m':(lm['hand.L'][0]-grip).length,'left_ankle_z':lm['foot.L'][0].z,'right_ankle_z':lm['foot.R'][0].z})

for f in range(1,301):
    for a,b in zip(POSES,POSES[1:]):
        if a[0]<=f<=b[0]:
            t=(f-a[0])/(b[0]-a[0]);t=t*t*(3-2*t)
            p=[f]+[a[i]+(b[i]-a[i])*t if isinstance(a[i],(int,float)) else tuple(Vector(a[i]).lerp(Vector(b[i]),t)) for i in range(1,len(a))]
            set_pose(f,p);break
action=rig.animation_data.action;action.name='AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory'
for fc in action.fcurves:
    for key in fc.keyframe_points:key.interpolation='LINEAR' # 60fps samples of the smoothstep motion
(QA/'animation-target-diagnostics.json').write_text(json.dumps({'method':'Analytical two-bone solve with explicit elbow and knee pole vectors; samples do not prove mesh contact','frames':metrics},indent=2),encoding='utf-8')

scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64
scene.render.fps=60;scene.frame_start=1;scene.frame_end=300;scene.view_settings.view_transform='AgX';scene.world.color=(.16,.16,.16)
for name,f in [('Provoke',1),('Bash',50),('MagnumBreak',145),('Endure',235),('Victory',275)]:scene.timeline_markers.new(name,frame=f)
scene.frame_set(1)
meshes=[o for o in character.objects if o.type=='MESH']
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
problems=[]
for o in meshes:
    for v in o.data.vertices:
        values=[g.weight for g in v.groups if g.weight>1e-6]
        if not values or len(values)>4 or abs(sum(values)-1)>1e-5:problems.append(o.name+': weights');break
    bm=bmesh.new();bm.from_mesh(o.data);count=sum(not e.is_manifold for e in bm.edges);bm.free()
    if count:problems.append(o.name+': nonmanifold '+str(count))
if triangles>60000:problems.append('triangle budget')
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'triangles':triangles,'meshes':len(meshes),'bones':len(arm_data.bones),'frames':300,'fps':60,'problems':problems,'elapsed_seconds':time.monotonic()-started,'visual_acceptance':'not_run','manual_retopology':'not_done','skill_effects':'not_done'}
(QA/'construction-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if problems:raise RuntimeError('Construction defects: '+str(problems))
bpy.ops.object.select_all(action='DESELECT')
for o in character.objects:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_swordsman_combo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_yup=True,export_anim_slide_to_zero=True,export_skins=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;move_collection(floor,stage);floor.data.materials.append(material('ReviewFloor',(.18,.19,.21),rough=.9))
for name,loc,power,size in [('Key',(3,-4,5),700,4),('Fill',(-3,-2,3),350,3),('Rim',(0,3,4),800,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);stage.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',d);stage.objects.link(cam);d.type='ORTHO';scene.camera=cam
def camera(loc,target=(0,0,.9),scale=2.25):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale
views={'front':((0,-4,1.35),(0,0,.9),2.25),'side':((4,0,1.35),(0,0,.9),2.25),'back':((0,4,1.35),(0,0,.9),2.25),'three-quarter':((2.8,-4,2),(0,0,.9),2.25),'detail':((1.2,-4,1.75),(0,0,1.53),.62)}
scene.render.resolution_x=scene.render.resolution_y=1280;scene.render.resolution_percentage=100
for name,(loc,target,scale) in views.items():camera(loc,target,scale);scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)
camera((2.8,-4,2));scene.render.resolution_x=scene.render.resolution_y=640
for i,f in enumerate([1,25,50,75,100,120,145,170,195,220,255,300],1):
    scene.frame_set(f);scene.render.filepath=str(QA/('pose_%02d.png'%i));bpy.ops.render.render(write_still=True)
scene.frame_set(1);camera((2.8,-4,2));scene.render.resolution_x=scene.render.resolution_y=960
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_swordsman_master.blend'))
if args.render_animation:
    folder=QA/'frames-neutral';folder.mkdir(exist_ok=True);scene.render.filepath=str(folder/'frame_');bpy.ops.render.render(animation=True)
report['total_elapsed_seconds']=time.monotonic()-started;(QA/'construction-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RO_POSTPROCESS_COMPLETE '+json.dumps(report))
