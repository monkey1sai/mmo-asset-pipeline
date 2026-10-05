"""Blender 4.5 local character baseline. No network, external assets or autoexec.

Run in Blender: --background --factory-startup --disable-autoexec --python ...
-- --version v001 [--render-animation]. Outputs only to this repository.
This is asset construction, not a quality approval system.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
args = argparse.ArgumentParser()
args.add_argument('--version', choices=['v001', 'v002', 'v003', 'v004'], default='v001')
args.add_argument('--render-animation', action='store_true')
args = args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
started = time.monotonic()
OUT = ROOT / 'assets' / 'processed' / 'ro-swordsman-combo' / args.version
QA = ROOT / 'runs' / 'qa' / 'ro-swordsman-combo' / args.version
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
scene.render.fps = 60
scene.frame_start, scene.frame_end = 1, 300
scene.view_settings.view_transform = 'AgX'
scene.world.color = (.16, .16, .16)
character = bpy.data.collections.new('COL_Character')
scene.collection.children.link(character)
stage = bpy.data.collections.new('COL_ReviewStage')
scene.collection.children.link(stage)

def move_collection(obj, collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)

def material(name, rgb, metal=0, rough=.5):
    m = bpy.data.materials.new('MAT_'+name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    return m

M = {
    'skin': material('Skin', (.63,.38,.24), rough=.65),
    'silver': material('Steel', (.39,.45,.52), .72, .29),
    'edge': material('SteelEdge', (.65,.72,.78), .72, .25),
    'blue': material('IndigoWool', (.023,.055,.14), rough=.83),
    'white': material('IvoryLinen', (.71,.68,.56), rough=.88),
    'leather': material('OiledLeather', (.12,.054,.023), rough=.55),
    'trouser': material('CharcoalTwill', (.035,.025,.018), rough=.9),
    'gold': material('Brass', (.43,.23,.062), .7,.34),
    'hair': material('ChestnutHair', (.074,.028,.012), rough=.65),
    'hairlight': material('HairRidges', (.14,.056,.019), rough=.61),
    'ink': material('Lash', (.009,.007,.005), rough=.8),
    'eye': material('Sclera', (.79,.79,.72), rough=.4),
    'iris': material('AmberIris', (.17,.074,.017), rough=.3),
}
WELD=[]
REST = {'root':((0,0,0),(0,0,.18)),
        'pelvis':((0,0,.88),(0,0,1.0)),
        'spine_01':((0,0,1.0),(0,0,1.17)),
        'spine_02':((0,0,1.17),(0,0,1.36)),
        'neck':((0,0,1.36),(0,0,1.45)),
        'head':((0,0,1.45),(0,0,1.7))}
PARENTS={'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
for side,s in [('L',1),('R',-1)]:
    d={
        'clavicle':((0,0,1.32),(s*.23,0,1.32)),
        'upper_arm':((s*.23,0,1.32),(s*.395,0,1.12)),
        'lower_arm':((s*.395,0,1.12),(s*.46,0,.915)),
        'hand':((s*.46,0,.915),(s*.48,0,.835)),
        'upper_leg':((s*.12,0,.90),(s*.125,0,.50)),
        'lower_leg':((s*.125,0,.50),(s*.13,0,.12)),
        'foot':((s*.13,0,.12),(s*.13,-.145,.05)),
        'toe':((s*.13,-.145,.05),(s*.13,-.22,.05)),
        'coat':((s*.13,.03,.87),(s*.24,.05,.52)),
    }
    for name,points in d.items(): REST[name+'.'+side]=points
    for name,parent in [('clavicle','spine_02'),('upper_arm','clavicle.'+side),('lower_arm','upper_arm.'+side),('hand','lower_arm.'+side),('upper_leg','pelvis'),('lower_leg','upper_leg.'+side),('foot','lower_leg.'+side),('toe','foot.'+side),('coat','pelvis')]:
        PARENTS[name+'.'+side]=parent
REST['sword']=((-.48,-.05,.85),(-.48,-.05,1.80))
PARENTS['sword']='hand.R'
arm_data=bpy.data.armatures.new('RO_Humanoid')
rig=bpy.data.objects.new('RIG_RO_Swordsman',arm_data)
character.objects.link(rig)
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,(head,tail) in REST.items():
    b=arm_data.edit_bones.new(name)
    b.head,b.tail=head,tail
    if PARENTS[name]: b.parent=arm_data.edit_bones[PARENTS[name]]
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front=True

def mesh(name, verts, faces, mat, bone=None, weight_fn=None):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    bm=bmesh.new(); bm.from_mesh(data)
    before=len(bm.verts)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    WELD.append({'object':name,'vertices_before':before,'vertices_after':len(bm.verts),'merged':before-len(bm.verts)})
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data); bm.free()
    obj=bpy.data.objects.new('SM_'+name,data)
    character.objects.link(obj)
    data.materials.append(M[mat])
    for p in data.polygons: p.use_smooth=True
    if bone or weight_fn:
        for i,v in enumerate(data.vertices):
            ws=weight_fn(v.co) if weight_fn else {bone:1.0}
            for bn,w in ws.items():
                group=obj.vertex_groups.get(bn) or obj.vertex_groups.new(name=bn)
                group.add([i],w,'REPLACE')
        mod=obj.modifiers.new('Skin','ARMATURE'); mod.object=rig
        obj.parent=rig
    return obj

def loft(name,rings,mat,bone=None,weight_fn=None,n=20):
    # rings: centre, radius_x, radius_y; elliptical sections in XY plane.
    verts=[]
    for c,rx,ry in rings:
        verts.extend([(c[0]+rx*math.cos(2*math.pi*j/n),c[1]+ry*math.sin(2*math.pi*j/n),c[2]) for j in range(n)])
    faces=[]
    for k in range(len(rings)-1):
        for j in range(n): faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    for k in [0,len(rings)-1]:
        centre=len(verts); verts.append(rings[k][0])
        for j in range(n): faces.append((centre,k*n+(j+1)%n,k*n+j))
    return mesh(name,verts,faces,mat,bone,weight_fn)

def ellipsoid(name,center,scale,mat,bone,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
    obj=bpy.context.object; obj.name='SM_'+name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    move_collection(obj,character)
    obj.data.materials.append(M[mat])
    for p in obj.data.polygons: p.use_smooth=True
    g=obj.vertex_groups.new(name=bone); g.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Skin','ARMATURE'); mod.object=rig; obj.parent=rig
    return obj

def tube(name,a,b,rad_a,rad_b,mat,bone,n=16):
    a,b=Vector(a),Vector(b)
    direction=(b-a).normalized()
    u=direction.cross(Vector((0,1,0))).normalized()
    v=direction.cross(u).normalized()
    verts=[]
    for t,r in [(0,rad_a),(.12,rad_a),(.88,rad_b),(1,rad_b)]:
        c=a.lerp(b,t)
        verts += [tuple(c+r*(u*math.cos(j*2*math.pi/n)+v*math.sin(j*2*math.pi/n))) for j in range(n)]
    faces=[(k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j) for k in range(3) for j in range(n)]
    verts.extend([tuple(a),tuple(b)])
    for j in range(n): faces.extend([(4*n,j,(j+1)%n),(4*n+1,3*n+(j+1)%n,3*n+j)])
    return mesh(name,verts,faces,mat,bone)

def line(name,points,radius,mat,bone):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='3D'
    curve.bevel_depth=radius; curve.bevel_resolution=2; curve.resolution_u=8
    curve.use_fill_caps=True
    spline=curve.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co; p.handle_left_type=p.handle_right_type='AUTO'
    ob=bpy.data.objects.new(name,curve); character.objects.link(ob)
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.ops.object.convert(target='MESH'); ob=bpy.context.object
    # Rebuild as a skinned mesh, with world coordinates retained.
    vs=[tuple(v.co) for v in ob.data.vertices]; fs=[tuple(p.vertices) for p in ob.data.polygons]
    bpy.data.objects.remove(ob,do_unlink=True)
    return mesh(name,vs,fs,mat,bone)

def torso_weights(v):
    t=min(1,max(0,(v.z-1.05)/.22))
    return {'spine_01':1-t,'spine_02':t}

loft('Tunic',[((0,0,.86),.17,.105),((0,0,.97),.155,.10),((0,0,1.10),.16,.11),((0,0,1.25),.20,.115),((0,0,1.34),.20,.10)],'blue',weight_fn=torso_weights)
loft('Breastplate',[((0,0,1.02),.157,.109),((0,0,1.10),.182,.119),((0,0,1.22),.209,.129),((0,0,1.30),.199,.114)],'silver','spine_02',n=32)
for z,rx,ry in [(1.03,.162,.115),(1.10,.185,.125),(1.295,.20,.119)]:
    loft('PlateTrim_'+str(z),[((0,0,z),rx,ry),((0,0,z+.012),rx,ry)],'edge','spine_02',n=32)
line('PlateCentralRidge',[(0,-.129,1.28),(0,-.137,1.20),(0,-.127,1.10)],.005,'edge','spine_02')
loft('Belt',[((0,0,.945),.17,.119),((0,0,.987),.17,.119)],'leather','pelvis',n=32)
ellipsoid('Buckle',(0,-.125,.965),(.034,.008,.024),'gold','pelvis',16,8)
loft('Neck',[((0,0,1.34),.057,.053),((0,0,1.455),.052,.046)],'skin','neck')
loft('Collar',[((0,0,1.33),.077,.066),((0,0,1.39),.067,.058)],'blue','neck')
loft('Face',[((0,-.009,1.445),.027,.04),((0,-.008,1.478),.066,.065),((0,0,1.515),.088,.081),((0,0,1.56),.095,.09),((0,.005,1.62),.087,.087),((0,.01,1.67),.055,.064),((0,.015,1.687),.016,.025)],'skin','head',n=40)
for s,side in [(1,'L'),(-1,'R')]:
    ellipsoid('Ear.'+side,(s*.094,0,1.55),(.017,.024,.034),'skin','head',16,8)
    # Eye outlines and small amber pupils, no shader-only facial features.
    x=s*.040
    if args.version in ['v001','v002']:
        ellipsoid('EyeOutline.'+side,(x,-.081,1.568),(.039,.011,.023),'ink','head')
        ellipsoid('Eye.'+side,(x,-.090,1.569),(.033,.008,.017),'eye','head')
        ellipsoid('Iris.'+side,(x,-.097,1.568),(.012,.003,.014),'iris','head',20,10)
        ellipsoid('Pupil.'+side,(x,-.100,1.568),(.006,.002,.009),'ink','head',16,8)
        ellipsoid('Catchlight.'+side,(x-.004,-.102,1.574),(.003,.001,.004),'eye','head',12,8)
    else:
        # Thin almond eyelids conform to the face instead of protruding eyeballs.
        outline=[(-1,0),(-.55,.70),(.2,.80),(1,.15),(.55,-.45),(-.30,-.40)]
        for name,w,h,offset,mat in [('Eyelid',.033,.015,.005,'ink'),('Eye',.030,.011,.006,'eye')]:
            vs=[]
            for dx,dz in outline:
                xx=x+dx*w; zz=1.566+dz*h
                yy=-.094+2.5*xx*xx+.6*(zz-1.55)**2-offset
                vs.append((xx,yy,zz))
            # Closed, thin eyelid shell rather than an open textured card.
            vs += [(xx,yy+.002,zz) for xx,yy,zz in vs]
            fs=[tuple(range(6)),tuple(reversed(range(6,12)))]+[(j,(j+1)%6,(j+1)%6+6,j+6) for j in range(6)]
            mesh(name+'.'+side,vs,fs,mat,'head')
        yy=-.100+2.5*x*x
        ellipsoid('Iris.'+side,(x,yy-.001,1.567),(.008,.0015,.009),'iris','head',20,10)
        ellipsoid('Pupil.'+side,(x,yy-.002,1.567),(.004,.001,.007),'ink','head',16,8)
        ellipsoid('Catchlight.'+side,(x-.003,yy-.003,1.571),(.002,.0005,.002),'eye','head',12,8)
    line('Brow.'+side,[(s*.015,-.086,1.592),(s*.038,-.090,1.599),(s*.070,-.077,1.592)],.0045,'hair','head')
mesh('Nose',[(-.009,-.077,1.567),(.009,-.077,1.567),(-.012,-.088,1.523),(.012,-.088,1.523),(0,-.112,1.526),(0,-.075,1.515)],[(0,1,4),(1,3,4),(3,5,4),(5,2,4),(2,0,4),(0,2,5,3,1)],'skin','head')
if args.version in ['v001','v002']:
    line('Mouth',[(-.022,-.066,1.493),(0,-.073,1.491),(.022,-.066,1.493)],.0018,'leather','head')
else:
    line('Mouth',[(-.021,-.082,1.493),(0,-.085,1.491),(.021,-.082,1.493)],.0013,'leather','head')
ellipsoid('HairCap',(0,.020,1.651 if args.version in ['v003','v004'] else 1.627),(.100,.096,.071 if args.version in ['v003','v004'] else .085),'hair','head',32,16)

def hair_lock(name,a,b,width,depth,mat='hair'):
    a,b=Vector(a),Vector(b)
    mid=a.lerp(b,.45); front=Vector((0,-depth,0))
    verts=[tuple(a+Vector((-width,0,0))),tuple(a+Vector((width,0,0))),tuple(mid+front),tuple(mid-Vector((0,depth*.5,0))),tuple(b)]
    return mesh(name,verts,[(0,1,2),(1,0,3),(0,2,4),(2,1,4),(1,3,4),(3,0,4)],mat,'head')
for i in range(18):
    a=2*math.pi*i/18
    c=Vector((.071*math.cos(a),.014+.06*math.sin(a),1.66))
    tip=Vector((.133*math.cos(a+.13),.014+.11*math.sin(a+.13),1.69+.038*math.sin(i*3.1)))
    if args.version in ['v003','v004']:
        c.z+=.013; tip.z+=.028*(1+math.cos(a))
    hair_lock('Crown_'+str(i),c,tip,.028,.027,'hairlight' if i%4==0 else 'hair')
for i in range(7):
    x=(i-3)*.025
    if args.version in ['v001','v002']:
        hair_lock('Fringe_'+str(i),(x,-.057,1.658),(x+.018,-.097,1.58-.028*(i%3)),.025,.02)
    else:
        hair_lock('Fringe_'+str(i),(x,-.057,1.676),(x+.015,-.095,1.608-.012*(i%3)),.024,.017)

for side,s in [('L',1),('R',-1)]:
    upper='upper_arm.'+side; lower='lower_arm.'+side; hand='hand.'+side
    tube('Sleeve.'+side,*REST[upper],.066,.053,'blue',upper)
    ellipsoid('Shoulder.'+side,(s*.235,0,1.31),(.097,.088,.102),'silver',upper)
    for j in range(3):
        ellipsoid('ShoulderLame_'+str(j)+'.'+side,(s*(.25+j*.018),0,1.29-j*.04),(.08-j*.005,.084,.031),'edge' if j==0 else 'silver',upper)
    tube('Forearm.'+side,*REST[lower],.050,.033,'leather',lower)
    a,b=map(Vector,REST[lower]); d=b-a
    tube('Vambrace.'+side,a+d*.04,a+d*.68,.056,.043,'silver',lower)
    for j in range(3):
        tube('VambraceTrim_'+str(j)+'.'+side,a+d*(j*.21),a+d*(j*.21+.06),.057-j*.004,.057-j*.004,'edge',lower)
    ellipsoid('Elbow.'+side,REST[lower][0],(.057,.062,.053),'silver',lower)
    ellipsoid('Glove.'+side,(s*.477,-.005,.857),(.042,.041,.052),'leather',hand)
    for j in range(4):
        ellipsoid('Finger_'+str(j)+'.'+side,(s*(.455+j*.012),-.029,.856),(.008,.023,.032),'leather',hand,12,8)
    ellipsoid('Thumb.'+side,(s*.443,-.038,.870),(.012,.021,.027),'leather',hand,12,8)
    # Segmented fabric legs; overlapping knee coverage hides only the garment seam.
    tube('TrouserThigh.'+side,*REST['upper_leg.'+side],.087,.062,'trouser','upper_leg.'+side)
    tube('TrouserShin.'+side,*REST['lower_leg.'+side],.061,.045,'trouser','lower_leg.'+side)
    ellipsoid('Knee.'+side,(s*.125,-.025,.50),(.068,.058,.060),'leather','lower_leg.'+side)
    tube('BootShaft.'+side,(s*.13,0,.10),(s*.126,0,.39),.052,.059,'leather','lower_leg.'+side)
    for z in [.16,.31,.38]:
        loft('BootStrap_'+str(z)+'.'+side,[((s*.13,0,z),.058,.059),((s*.13,0,z+.014),.058,.059)],'leather','lower_leg.'+side)
    ellipsoid('BootFoot.'+side,(s*.13,-.075,.066),(.058,.126,.063),'leather','foot.'+side)
    ellipsoid('BootSole.'+side,(s*.13,-.075,.022),(.061,.132,.018),'trouser','foot.'+side)
    loft('CoatTail.'+side,[((s*.13,.026,.91),.075,.083),((s*.175,.045,.76),.087,.065),((s*.235,.06,.57),.076,.044),((s*.23,.06,.535),.07,.038)],'blue','coat.'+side,n=16)
    line('CoatPiping.'+side,[(s*.21,-.033,.88),(s*.27,.005,.72),(s*.29,.029,.55)],.005,'edge','coat.'+side)
    ellipsoid('BeltPouch.'+side,(s*.183,.016,.905),(.046,.061,.060),'leather','pelvis',16,8)
loft('WhiteTabard',[((0,-.099,.955),.066,.012),((0,-.116,.82),.075,.012),((0,-.141,.59),.081,.012),((0,-.142,.56),.085,.012)],'white','pelvis',n=16)
line('TabardHem',[(-.08,-.151,.569),(0,-.157,.566),(.08,-.151,.569)],.003,'white','pelvis')

# Straight sword, separate weighted object attached to explicit weapon bone.
sx,sy,sz=REST['sword'][0]
loft('SwordGrip',[((sx,sy,sz-.066),.018,.014),((sx,sy,sz+.07),.018,.014)],'leather','sword',n=16)
ellipsoid('Pommel',(sx,sy,sz-.075),(.026,.020,.022),'gold','sword',16,8)
tube('Crossguard',(sx-.10,sy,sz+.084),(sx+.10,sy,sz+.084),.018,.018,'gold','sword')
verts=[]
for z,w in [(sz+.10,.029),(sz+.65,.025),(sz+.92,0.0005)]:
    verts.extend([(sx-w,sy,z),(sx,sy-.006,z),(sx+w,sy,z),(sx,sy+.006,z)])
faces=[(k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j) for k in range(2) for j in range(4)]
faces.extend([(3,2,1,0),(8,9,10,11)])
mesh('SwordBlade',verts,faces,'edge','sword')

# Key targets in character coordinates. +Z up, -Y facing. Each state is interpolated
# with smoothstep, then two-bone solving produces continuous joint orientations.
# (frame, hip height, chest lean, yaw, right hand, sword direction, left hand,
#  left foot, right foot). Hand targets are bounded by exact arm lengths.
POSES=[
 (1,.88,0,0,(-.27,-.29,1.00),(-.55,-.10,.83),(-.19,-.28,1.04),(.23,0,.12),(-.23,0,.12)),
 (25,.90,0,-.12,(-.28,-.18,1.22),(-.45,0,.89),(-.13,-.23,1.14),(.23,0,.12),(-.23,0,.12)),
 (50,.85,-.10,-.25,(-.22,.01,1.60),(.12,.09,.99),(-.15,.03,1.53),(.21,-.13,.12),(-.23,.09,.12)),
 (75,1.03,-.18,0,(-.20,.03,1.66),(.1,-.10,.99),(.25,-.22,1.24),(.23,-.20,.25),(-.23,.10,.27)),
 (100,1.04,-.15,0,(-.15,-.15,1.74),(0,-.5,.86),(-.11,-.13,1.68),(.23,-.20,.18),(-.23,.16,.22)),
 (120,.80,-.25,.12,(-.15,-.43,.90),(.03,-.88,-.48),(-.10,-.38,.96),(.21,-.13,.12),(-.24,.08,.12)),
 (145,.87,.03,.65,(-.32,.06,1.18),(-.90,.30,.15),(.22,-.12,1.20),(.23,0,.12),(-.23,0,.12)),
 (170,.79,-.23,.05,(-.12,-.33,1.00),(0,-.12,-.99),(-.07,-.28,1.07),(.24,-.07,.12),(-.24,.07,.12)),
 (195,.83,0,-.65,(-.36,-.20,1.10),(-.99,-.05,.1),(.20,-.27,1.16),(.25,0,.12),(-.25,0,.12)),
 (220,.88,-.05,.10,(-.33,-.23,1.15),(-.9,-.34,.27),(.30,-.24,1.19),(.24,0,.12),(-.24,0,.12)),
 (255,.91,0,0,(-.22,-.17,1.03),(-.3,-.12,-.95),(.23,-.14,1.07),(.14,0,.12),(-.14,0,.12)),
 (280,.91,0,0,(-.20,-.18,1.00),(.43,.10,-.89),(.16,-.20,.99),(.14,0,.12),(-.14,0,.12)),
 (300,.91,0,0,(-.20,-.18,1.00),(.43,.10,-.89),(.16,-.20,.99),(.14,0,.12),(-.14,0,.12)),
]

def solve(a,target,length1,length2,pole):
    a,target,pole=Vector(a),Vector(target),Vector(pole)
    direction=target-a; distance=direction.length
    distance=min(length1+length2-.002,max(abs(length1-length2)+.002,distance))
    d=direction.normalized(); target=a+d*distance
    p=pole-d*pole.dot(d)
    if p.length<.001: p=Vector((0,1,0))
    p.normalize()
    along=(length1*length1-length2*length2+distance*distance)/(2*distance)
    height=math.sqrt(max(0,length1*length1-along*along))
    return a+d*along+p*height,target

def bone_matrix(head,tail,reference=Vector((0,1,0))):
    y=(Vector(tail)-Vector(head)).normalized()
    x=y.cross(reference)
    if x.length<.001: x=y.cross(Vector((1,0,0)))
    x.normalize(); z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_4x4().copy() @ Matrix.Identity(4)

def set_pose(frame,pose):
    _,hz,lean,yaw,rh,sd,lh,lf,rf=pose
    yawmat=Matrix.Rotation(yaw,3,'Z')
    def world(p): return yawmat @ Vector(p)
    hip=Vector((0,0,hz)); spine1=hip+world((0,0,.12))
    spine2=spine1+world((0,lean*.38,.17))
    neck=spine2+world((0,lean*.40,.19)); head=neck+world((0,0,.09))
    landmarks={'root':(Vector((0,0,0)),Vector((0,0,.18))),
        'pelvis':(hip,spine1),'spine_01':(spine1,spine2),'spine_02':(spine2,neck),
        'neck':(neck,head),'head':(head,head+world((0,0,.25)))}
    for side,s,ht,ft in [('L',1,lh,lf),('R',-1,rh,rf)]:
        shoulder=neck+world((s*.23,0,-.04))
        elbow,wrist=solve(shoulder,world(ht),.2593,.2151,world((s,1,-.3)))
        handtail=wrist+world((0,0,-.08))
        th=hip+world((s*.12,0,.02))
        knee,ankle=solve(th,Vector(ft),.4,.38,Vector((0,-1,0)))
        toe=ankle+world((0,-.145,-.07))
        landmarks.update({'clavicle.'+side:(neck+world((0,0,-.04)),shoulder),
            'upper_arm.'+side:(shoulder,elbow),'lower_arm.'+side:(elbow,wrist),
            'hand.'+side:(wrist,handtail),'upper_leg.'+side:(th,knee),
            'lower_leg.'+side:(knee,ankle),'foot.'+side:(ankle,toe),
            'toe.'+side:(toe,toe+world((0,-.075,0))),
            'coat.'+side:(hip+world((s*.13,.03,-.01)),hip+world((s*(.24+.02*math.sin(frame*.07)),.05+.025*math.sin(frame*.11),-.36)))})
    grip=landmarks['hand.R'][0]+world((-.014,-.045,-.055))
    landmarks['sword']=(grip,grip+world(sd).normalized()*.95)
    pose_matrices={}
    for name,(a,b) in landmarks.items():
        reference=world(arm_data.bones[name].matrix_local.to_3x3().col[2]) if args.version!='v001' else world((0,1,0))
        matrix=bone_matrix(a,b,reference)
        matrix.translation=a
        pb=rig.pose.bones[name]
        parent=PARENTS[name]
        rest=arm_data.bones[name].matrix_local
        pb.matrix_basis=(rest.inverted() @ arm_data.bones[parent].matrix_local @ pose_matrices[parent].inverted() @ matrix) if parent else rest.inverted() @ matrix
        pose_matrices[name]=matrix
        pb.rotation_mode='QUATERNION'
        pb.keyframe_insert('location',frame=frame,group=name)
        pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)

for f in range(1,301):
    for a,b in zip(POSES,POSES[1:]):
        if a[0]<=f<=b[0]:
            t=(f-a[0])/(b[0]-a[0]); t=t*t*(3-2*t)
            state=[f]+[a[i]+(b[i]-a[i])*t if isinstance(a[i],(int,float)) else tuple(Vector(a[i]).lerp(Vector(b[i]),t)) for i in range(1,len(a))]
            set_pose(f,state); break
action=rig.animation_data.action
action.name='AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory'
for fc in action.fcurves:
    for k in fc.keyframe_points: k.interpolation='LINEAR'
scene.timeline_markers.new('Provoke',frame=1)
scene.timeline_markers.new('Bash',frame=50)
scene.timeline_markers.new('MagnumBreak',frame=145)
scene.timeline_markers.new('Endure',frame=235)
scene.timeline_markers.new('Victory',frame=275)

# Numerical validation before export. It does not establish visual acceptance.
scene.frame_set(1)
meshes=[ob for ob in character.objects if ob.type=='MESH']
triangles=sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in meshes)
problems=[]
for ob in meshes:
    if tuple(ob.scale)!=(1,1,1): problems.append(ob.name+': scale')
    for v in ob.data.vertices:
        ws=[g.weight for g in v.groups if g.weight>1e-8]
        if not ws or len(ws)>4 or abs(sum(ws)-1)>1e-5: problems.append(ob.name+': weights'); break
    bm=bmesh.new(); bm.from_mesh(ob.data)
    count=sum(not e.is_manifold for e in bm.edges)
    if count: problems.append(ob.name+': nonmanifold '+str(count))
    bm.free()
if triangles>60000: problems.append('triangle budget')
validation={'tool':bpy.app.version_string,'meshes':len(meshes),'triangles':triangles,'bones':len(arm_data.bones),'max_influences':4,'frames':300,'fps':60,'problems':problems,'weld':WELD,'visual_acceptance':'not_run','elapsed_seconds':time.monotonic()-started}
(QA/'construction-check.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
if problems: raise RuntimeError('pre-export validation: '+str(problems))
bpy.ops.object.select_all(action='DESELECT')
for ob in character.objects: ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_swordsman_combo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_yup=True,export_anim_slide_to_zero=True,export_skins=True,export_materials='EXPORT',export_cameras=False,export_lights=False)

# Stage separated from export collection.
floor=material('ReviewFloor',(.18,.19,.21),rough=.9)
bpy.ops.mesh.primitive_plane_add(size=200)
plane=bpy.context.object; plane.name='ReviewFloor'; plane.data.materials.append(floor); move_collection(plane,stage)
for name,location,power,size in [('Key',(3,-4,5),700,4),('Fill',(-3,-2,3),350,3),('Rim',(0,3,4),800,3)]:
    ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
    ob=bpy.data.objects.new(name,ld); stage.objects.link(ob); ob.location=location
    ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('ReviewCamera'); cam=bpy.data.objects.new('ReviewCamera',camdata); stage.objects.link(cam)
camdata.type='ORTHO'; camdata.ortho_scale=2.25; scene.camera=cam
def camera(location,target=(0,0,.9),scale=2.25):
    cam.location=location; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); camdata.ortho_scale=scale
views={'front':((0,-4,1.35),(0,0,.9),2.25),'side':((4,0,1.35),(0,0,.9),2.25),'back':((0,4,1.35),(0,0,.9),2.25),'three-quarter':((2.8,-4,2),(0,0,.9),2.25),'detail':((1.2,-4,1.75),(0,0,1.53),.62)}
scene.frame_set(1)
for name,(loc,target,scale) in views.items():
    camera(loc,target,scale)
    scene.render.filepath=str(QA/(name+'.png')); bpy.ops.render.render(write_still=True)
camera((2.8,-4,2))
scene.render.resolution_x=scene.render.resolution_y=640
for i,f in enumerate([1,25,50,75,100,120,145,170,195,220,255,300],1):
    scene.frame_set(f); scene.render.filepath=str(QA/('pose_%02d.png'%i)); bpy.ops.render.render(write_still=True)
scene.frame_set(1); camera((2.8,-4,2))
scene.render.resolution_x=960; scene.render.resolution_y=960
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_swordsman_master.blend'))
if args.render_animation:
    frames=QA/'frames'; frames.mkdir(exist_ok=True)
    scene.render.filepath=str(frames/'frame_'); scene.render.image_settings.file_format='PNG'
    bpy.ops.render.render(animation=True)
validation['total_elapsed_seconds']=time.monotonic()-started
(QA/'construction-check.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
print('RO_BUILD_COMPLETE '+json.dumps(validation))
