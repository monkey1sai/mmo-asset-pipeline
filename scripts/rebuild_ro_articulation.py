"""Local source-preserving reconstruction, inspected preflight before full animation.

Planar, explicitly selected source parts retain UVs. New joints have authored
quad rings and bounded weights; no arbitrary-region centroid-fan sealing.
"""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_review_common import material, stage, render_views, camera
p=argparse.ArgumentParser(); p.add_argument('--stage',choices=['preflight','full'],default='preflight'); p.add_argument('--version',choices=['v001','v002','v003'],default='v001')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'assets/processed/ro-swordsman-combo-r002'/a.version
QA=ROOT/'runs/qa/ro-swordsman-combo-r002'/a.version
OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)
source=ROOT/'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='9350ee0a6cbe9af02bedabcc7ccee01153b7af90edc7f604dae67d205999e4c1'
tree=ast.parse((ROOT/'scripts/build_ro_swordsman.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'solve','bone_matrix'} or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POSES' for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<inspected pose mathematics>','exec'),globals())

REST={'root':((0,0,0),(0,0,.18)),'pelvis':((0,0,.86),(0,0,.98)),'spine_01':((0,0,.98),(0,0,1.15)),'spine_02':((0,0,1.15),(0,0,1.34)),'neck':((0,0,1.34),(0,0,1.43)),'head':((0,0,1.43),(0,0,1.69))}
PARENTS={'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
for side,s in [('L',1),('R',-1)]:
    for name,ends,parent in [
        ('clavicle',((0,0,1.30),(s*.24,0,1.30)),'spine_02'),
        ('upper_arm',((s*.24,0,1.30),(s*.44,0,1.10)),'clavicle.'+side),
        ('lower_arm',((s*.44,0,1.10),(s*.58,-.015,.89)),'upper_arm.'+side),
        ('hand',((s*.58,-.015,.89),(s*.58,-.095,.89)),'lower_arm.'+side),
        ('upper_leg',((s*.12,0,.88),(s*.16,0,.47)),'pelvis'),
        ('lower_leg',((s*.16,0,.47),(s*.18,-.02,.09)),'upper_leg.'+side),
        ('foot',((s*.18,-.02,.09),(s*.18,-.16,.035)),'lower_leg.'+side),
        ('toe',((s*.18,-.16,.035),(s*.18,-.22,.035)),'foot.'+side),
        ('coat',((s*.13,.025,.87),(s*.23,.04,.49)),'pelvis')]:
        REST[name+'.'+side]=ends; PARENTS[name+'.'+side]=parent
REST['sword']=((-.58,-.070,.89),(-.58,-.070,1.84)); PARENTS['sword']='hand.R'

def skin(ob,weight_fn):
    for v in ob.data.vertices:
        weights={n:max(0,w) for n,w in weight_fn(v.co).items() if w>1e-7}
        weights=dict(sorted(weights.items(),key=lambda i:-i[1])[:4]); total=sum(weights.values())
        if not total: raise ValueError('Unweighted vertex '+ob.name)
        for name,value in weights.items():
            group=ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name); group.add([v.index],value/total,'REPLACE')
    mod=ob.modifiers.new('Skin','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True; ob.parent=rig
    return ob

def mesh(name,vertices,faces,mat,bone=None,weights=None):
    data=bpy.data.meshes.new(name); data.from_pydata(vertices,[],faces); data.update()
    ob=bpy.data.objects.new('SM_'+name,data); char.objects.link(ob); data.materials.append(M[mat] if isinstance(mat,str) else mat)
    for f in data.polygons: f.use_smooth=True
    bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    if bone: skin(ob,lambda v:{bone:1})
    elif weights: skin(ob,weights)
    return ob

def tube(name,centers,radii,mat,bone=None,ringweights=None,n=20,flatten=1):
    centers=[Vector(c) for c in centers]; verts=[]; faces=[]
    for i,(c,r) in enumerate(zip(centers,radii)):
        d=(centers[min(i+1,len(centers)-1)]-centers[max(i-1,0)]).normalized()
        ref=Vector((0,1,0)) if abs(d.y)<.95 else Vector((1,0,0)); u=d.cross(ref).normalized(); v=d.cross(u)
        for j in range(n): verts.append(c+r*(u*math.cos(j*math.tau/n)+v*math.sin(j*math.tau/n)*flatten))
    for i in range(len(centers)-1):
        for j in range(n): faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
    faces.extend([tuple(reversed(range(n))),tuple(range((len(centers)-1)*n,len(centers)*n))])
    ob=mesh(name,verts,faces,mat)
    if bone: skin(ob,lambda v:{bone:1})
    elif ringweights:
        for idx,weights in enumerate(ringweights):
            total=sum(weights.values())
            for b,w in weights.items():
                group=ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b); group.add(list(range(idx*n,(idx+1)*n)),w/total,'REPLACE')
        mod=ob.modifiers.new('Skin','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True; ob.parent=rig
    return ob

def ellipsoid(name,center,radius,mat,bone,n=24,rings=12):
    vs=[Vector(center)+Vector((0,0,-radius[2]))]; fs=[]
    for i in range(1,rings):
        t=math.pi*i/rings
        for j in range(n):
            q=math.tau*j/n; vs.append(Vector(center)+Vector((radius[0]*math.sin(t)*math.cos(q),radius[1]*math.sin(t)*math.sin(q),-radius[2]*math.cos(t))))
    vs.append(Vector(center)+Vector((0,0,radius[2]))); last=len(vs)-1
    for j in range(n): fs.append((0,1+(j+1)%n,1+j)); fs.append((last,1+(rings-2)*n+j,1+(rings-2)*n+(j+1)%n))
    for i in range(rings-2):
        for j in range(n): fs.append((1+i*n+j,1+i*n+(j+1)%n,1+(i+1)*n+(j+1)%n,1+(i+1)*n+j))
    return mesh(name,vs,fs,mat,bone)

def source_part(name,planes,bone,transform=None):
    """Keep negative sides of deliberate planar cuts, cap only plane contours."""
    data=original.data.copy(); ob=bpy.data.objects.new('SM_Source_'+name,data); char.objects.link(ob)
    cap_material=0
    if a.version=='v003':
        data.materials.append(M['leather'] if name.startswith('Boot') else M['darkmetal']); cap_material=len(data.materials)-1
    bm=bmesh.new(); bm.from_mesh(data)
    for co,no in planes:
        co,no=Vector(co),Vector(no)
        result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no,clear_outer=True,clear_inner=False)
        edges=[e for e in bm.edges if e.is_boundary and all(abs((v.co-co).dot(no))<1e-5 for v in e.verts)]
        if edges:
            caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
            for f in caps: f.material_index=cap_material
            if caps: bmesh.ops.triangulate(bm,faces=caps)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
    if a.version!='v001':
        remaining=set(bm.verts); components=[]
        while remaining:
            stack=[remaining.pop()]; group=[]
            while stack:
                v=stack.pop(); group.append(v)
                for e in v.link_edges:
                    n=e.other_vert(v)
                    if n in remaining: remaining.remove(n); stack.append(n)
            components.append(group)
        main=max(components,key=len)
        extra=[v for group in components if group is not main for v in group]
        if extra: bmesh.ops.delete(bm,geom=extra,context='VERTS')
    if transform:
        for v in bm.verts: v.co=transform@v.co
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    for f in data.polygons: f.use_smooth=True
    data.update(); source_selections.append({'part':name,'planes':planes,'vertices':len(data.vertices),'faces':len(data.polygons),'source_surface_retained':True,'cap_method':'coplanar contour triangulation, rigid part only'})
    skin(ob,lambda v:{bone:1}); return ob

def arm_transform(side,lower=False):
    s=1 if side=='L' else -1
    start=Vector((s*.30,-.015,1.07)) if lower else Vector((s*.24,0,1.30))
    end=Vector((s*.16,-.165,.935)) if lower else Vector((s*.29,-.005,1.06))
    newa,newb=map(Vector,REST[('lower_arm' if lower else 'upper_arm')+'.'+side])
    old=bone_matrix(start,end,Vector((0,1,0))); old.translation=start
    new=bone_matrix(newa,newb,Vector((0,1,0))); new.translation=newa
    return new@old.inverted()

if a.stage=='preflight':
    if (OUT/'ro_repair_bind.blend').exists(): raise RuntimeError('Preflight already saved; preserve attempt before a new version or documented implementation correction')
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    original=next(o for o in bpy.context.scene.objects if o.type=='MESH'); mw=original.matrix_world.copy()
    points=[mw@v.co for v in original.data.vertices]; low=Vector(tuple(min(v[i] for v in points) for i in range(3))); high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
    center=Vector(((high.x+low.x)/2,(high.y+low.y)/2,low.z)); factor=1.74/(high.z-low.z)
    for v in original.data.vertices:
        v.co=(mw@v.co-center)*factor
        if a.version!='v001': v.co.x+=.105
    original.parent=None; original.matrix_world=Matrix.Identity(4)
    bm=bmesh.new(); bm.from_mesh(original.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6); bm.to_mesh(original.data); bm.free(); original.data.update()
    char=bpy.data.collections.new('COL_Character'); bpy.context.scene.collection.children.link(char)
    effects=bpy.data.collections.new('COL_SkillEffects'); bpy.context.scene.collection.children.link(effects)
    M={
      'skin':material('Skin_WarmIvory',(.65,.48,.36),rough=.72), 'navy':material('Tunic_Navy',(.025,.065,.135),rough=.78),
      'pants':material('Trousers_Charcoal',(.028,.037,.049),rough=.86), 'ivory':material('Tabard_Ivory',(.78,.75,.65),rough=.88),
      'silver':material('Armor_SatinSilver',(.40,.48,.54),metal=.82,rough=.34), 'darkmetal':material('Armor_Recess',(.055,.072,.086),metal=.68,rough=.45),
      'trim':material('SilverTrim',(.52,.59,.62),metal=.8,rough=.30), 'leather':material('Gloves_BrownLeather',(.105,.048,.021),rough=.65),
      'gold':material('Sword_Brass',(.38,.21,.065),metal=.73,rough=.33), 'white':material('Eye_White',(.82,.84,.81),rough=.45),
      'iris':material('Eye_Brown',(.10,.040,.017),rough=.43), 'black':material('Eye_LashPupil',(.009,.006,.004),rough=.48),
      'shine':material('Eye_Catchlight',(.96,.97,.94),rough=.24), 'hair':material('Hair_Chestnut',(.14,.055,.024),rough=.6)}
    if a.version!='v001':
        M['navy'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.009,.024,.050,1)
    for m in original.data.materials:
        if m and m.use_nodes:
            for node in m.node_tree.nodes:
                if node.type=='NORMAL_MAP': node.inputs['Strength'].default_value=.08
            bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Roughness'].default_value=.42
    ad=bpy.data.armatures.new('RO_ArticulatedHumanoid'); rig=bpy.data.objects.new('ARM_RO_Swordsman',ad); char.objects.link(rig)
    bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
    for name,(h,t) in REST.items():
        b=ad.edit_bones.new(name); b.head=h; b.tail=t
        if PARENTS[name]: b.parent=ad.edit_bones[PARENTS[name]]
    bpy.ops.object.mode_set(mode='OBJECT'); rig.show_in_front=True
    source_selections=[]
    head=source_part('HeadHair', [((0,0,1.405),(0,0,-1))], 'head')
    chest=source_part('ChestArmor', [((0,0,1.405),(0,0,1)),((0,0,1.055),(0,0,-1)),((.185,0,0),(1,0,0)),((-.185,0,0),(-1,0,0))], 'spine_02')
    # Semantics explicitly inspected in bind views; no source arms/waist/weapon remain.
    for side,s in [('L',1),('R',-1)]:
        if a.version=='v003':
            source_part('Shoulder_'+side,[((s*.185,0,0),(-s,0,0)),((0,0,1.405),(0,0,1)),((0,0,1.255),(0,0,-1))],'clavicle.'+side)
            h,e=map(Vector,REST['upper_arm.'+side])
            for j,t in enumerate([.18,.36,.54]):
                tube('Lamellar%d_'%j+side,[h.lerp(e,t),h.lerp(e,t+.12)],[.072-j*.006,.070-j*.006],'silver','upper_arm.'+side,n=24)
                tube('LamellarTrim%d_'%j+side,[h.lerp(e,t+.10),h.lerp(e,t+.125)],[.073-j*.006,.073-j*.006],'trim','upper_arm.'+side,n=24)
        else:
            source_part('Shoulder_'+side,[((s*.185,0,0),(-s,0,0)),((0,0,1.405),(0,0,1)),((0,0,1.17),(0,0,-1))],'upper_arm.'+side,arm_transform(side))
        if a.version=='v001': source_part('Elbow_'+side,[((s*.245,0,0),(-s,0,0)),((0,0,1.17),(0,0,1)),((0,0,1.025),(0,0,-1))],'lower_arm.'+side,arm_transform(side,True))
        else:
            e=Vector(REST['lower_arm.'+side][0]); ellipsoid('ElbowPlate_'+side,e+Vector((0,-.038,0)),(.057,.037,.054),'silver','lower_arm.'+side,n=24,rings=12)
        boot=source_part('Boot_'+side,[((0,0,.355),(0,0,1)),((0,0,0),(-s,0,0))],'lower_leg.'+side)
        # Authored ankle blend, while preserving boot/sole source geometry and UV.
        boot.vertex_groups.clear(); boot.modifiers.clear()
        skin(boot,lambda v,side=side:{'foot.'+side:1-max(0,min(1,(v.z-.09)/.10)), 'lower_leg.'+side:max(0,min(1,(v.z-.09)/.10))})
    # Remove old painted closed eyes from the visible skin surface; keep hair UVs.
    image=next(i for i in bpy.data.images if i.name.startswith('texture_diffuse')); pixels=list(image.pixels); width,height=image.size
    head.data.materials.append(M['skin']); skin_index=len(head.data.materials)-1
    head.data.materials.append(M['hair']); uv=head.data.uv_layers.active
    face_labels=[]
    for f in head.data.polygons:
        v=f.center
        colors=[]
        for li in f.loop_indices:
            u,t=uv.data[li].uv; ix=max(0,min(width-1,int(u*width))); iy=max(0,min(height-1,int(t*height))); j=(iy*width+ix)*4; colors.append(pixels[j:j+3])
        rgb=[sum(c[k] for c in colors)/len(colors) for k in range(3)]
        if (v.y<-.05 and 1.425<v.z<1.585 and abs(v.x)<.102 and rgb[0]>.38 and rgb[1]/max(rgb[0],.001)>.73) if a.version=='v001' else (v.y<-.11 and 1.435<v.z<1.522 and abs(v.x)<.097 and f.normal.y<-.15):
            f.material_index=skin_index; face_labels.append(f.index)
        elif v.z>1.57 or rgb[1]/max(rgb[0],.001)<.68:
            # Retain texture/UVs for hair; darker color comes from multiply tint.
            pass
    for m in head.data.materials[:1]:
        # Tint existing diffuse using supported nodes; source pixels are never edited.
        bs=m.node_tree.nodes.get('Principled BSDF'); tex=next((n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('texture_diffuse')),None)
        if tex:
            mix=m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=.35; mix.inputs[2].default_value=(.68,.52,.40,1)
            m.node_tree.links.new(tex.outputs['Color'],mix.inputs[1]); m.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
    if a.version=='v003':
        bpy.context.view_layer.objects.active=head
        subs=head.modifiers.new('FaceHairRefinement','SUBSURF'); subs.levels=1; subs.render_levels=1
        bpy.ops.object.modifier_apply(modifier=subs.name)
    face_bvh=BVHTree.FromPolygons([v.co.copy() for v in head.data.vertices],[list(f.vertices) for f in head.data.polygons if f.material_index==skin_index],all_triangles=False)
    def face_point(x,z,offset=.001):
        point,normal,index,d=face_bvh.ray_cast(Vector((x,-.6,z)),Vector((0,1,0)),.65)
        if point is None:
            point,normal,index,d=face_bvh.find_nearest(Vector((x,-.15,z)))
            if point is None or d>.035: raise ValueError('No actual face surface at eye coordinate')
        return Vector((x,point.y-offset,z))
    def eye_patch(name,x,z,rx,rz,mat,offset,tilt=0):
        vs=[face_point(x,z,offset)]; fs=[]; count=48; rings=8
        for ring in range(1,rings+1):
            radius=ring/rings
            for j in range(count):
                q=j*math.tau/count; dx=rx*math.cos(q)*radius; dz=rz*math.sin(q)*radius+dx*tilt
                vs.append(face_point(x+dx,z+dz,offset))
        for j in range(count): fs.append((0,1+j,1+(j+1)%count))
        for ring in range(rings-1):
            for j in range(count): fs.append((1+ring*count+j,1+ring*count+(j+1)%count,1+(ring+1)*count+(j+1)%count,1+(ring+1)*count+j))
        return mesh(name,vs,fs,mat,'head')
    # Actual face-conforming geometry, not screen compositing or texture edits.
    for side,s in [('L',1),('R',-1)]:
        x=s*.048; y=-.109; z=1.537
        if a.version!='v001': x=s*.036; y=-.158; z=1.509
        if a.version=='v003':
            eye_patch('EyeLash_'+side,x,z,.025,.010,'black',.0010,tilt=s*.12)
            eye_patch('EyeWhite_'+side,x,z,.023,.008,'white',.0018,tilt=s*.12)
            eye_patch('EyeIris_'+side,x,z,.0064,.0078,'iris',.0025)
            eye_patch('EyePupil_'+side,x,z,.0028,.0055,'black',.0030)
            eye_patch('EyeCatchlight_'+side,x-.0016,z+.0025,.0015,.0018,'shine',.0035)
            points=[face_point(x+s*t*.025,z+.022+s*t*.006,.0012) for t in [-1,-.5,0,.5,1]]
            tube('Brow_'+side,points,[.001,.0022,.0025,.002,.0008],'hair','head',n=8)
            continue
        ellipsoid('EyeSclera_'+side,(x,y,z),(.027,.012,.0125),'white','head',n=24,rings=10)
        ellipsoid('EyeIris_'+side,(x,y-.011,z),(.0085,.0032,.011),'iris','head',n=20,rings=10)
        ellipsoid('EyePupil_'+side,(x,y-.014,z),(.0038,.0015,.0075),'black','head',n=16,rings=8)
        ellipsoid('EyeCatchlight_'+side,(x-.002,y-.0155,z+.004),(.002,.001,.0025),'shine','head',n=12,rings=6)
        lid=[(x+s*t*.026,y-.001,z+.008+.004*math.sin((t+1)*math.pi/2)+s*t*.004) for t in [-1,-.6,-.2,.2,.6,1]]
        tube('UpperLid_'+side,lid,[.0017]*6,'black','head',n=8)
        brow=[(x+s*t*.029,y+.001,z+.027+s*t*.005) for t in [-1,-.5,0,.5,1]]
        tube('Brow_'+side,brow,[.0025,.0033,.0034,.0025,.0013],'hair','head',n=8)
    # Quad-loop body, trousers and arm underlayers, with explicit joint transition rings.
    tube('WaistTunic',[(0,0,z) for z in [.83,.88,.93,.98,1.035,1.075]],[.19,.20,.195,.19,.19,.18],'navy',ringweights=[{'pelvis':1},{'pelvis':1},{'pelvis':.85,'spine_01':.15},{'pelvis':.45,'spine_01':.55},{'spine_01':.7,'spine_02':.3},{'spine_02':1}],n=32,flatten=.68)
    tube('WaistBelt',[(0,0,.886),(0,0,.919)],[.207,.207],'leather','pelvis',n=40,flatten=.68)
    buckle=mesh('BeltBuckle',[(-.04,-.148,.888),(.04,-.148,.888),(.04,-.148,.921),(-.04,-.148,.921),(-.04,-.157,.888),(.04,-.157,.888),(.04,-.157,.921),(-.04,-.157,.921)],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'gold','pelvis')
    for side,s in [('L',1),('R',-1)]:
        h,e=map(Vector,REST['upper_arm.'+side]); _,w=map(Vector,REST['lower_arm.'+side])
        centers=[h.lerp(e,t) for t in [0,.2,.55,.85,.97]]+[e.lerp(w,t) for t in [0,.08,.2,.5,.85,1]]
        radii=[.055,.065,.060,.047,.043,.043,.044,.045,.043,.035,.029]
        weights=[{'upper_arm.'+side:1}]*3+[{'upper_arm.'+side:.95,'lower_arm.'+side:.05},{'upper_arm.'+side:.65,'lower_arm.'+side:.35},{'upper_arm.'+side:.5,'lower_arm.'+side:.5},{'upper_arm.'+side:.35,'lower_arm.'+side:.65},{'upper_arm.'+side:.05,'lower_arm.'+side:.95}]+[{'lower_arm.'+side:1}]*3
        tube('SleeveJoint_'+side,centers,radii,'navy',ringweights=weights,n=24)
        tube('Bracer_'+side,[e.lerp(w,t) for t in [.24,.3,.78,.91]],[.050,.052,.044,.038],'silver','lower_arm.'+side,n=20)
        tube('BracerTrim_'+side,[e.lerp(w,t) for t in [.29,.33]],[.054,.054],'trim','lower_arm.'+side,n=20)
        th,k=map(Vector,REST['upper_leg.'+side]); _,ank=map(Vector,REST['lower_leg.'+side])
        legs=[th.lerp(k,t) for t in [0,.18,.45,.7,.86,.97]]+[k.lerp(ank,t) for t in [0,.10,.22,.4,.55]]
        lr=[.103,.105,.10,.088,.075,.068,.067,.068,.065,.057,.052]
        lw=[{'upper_leg.'+side:1}]*4+[{'upper_leg.'+side:.9,'lower_leg.'+side:.1},{'upper_leg.'+side:.65,'lower_leg.'+side:.35},{'upper_leg.'+side:.5,'lower_leg.'+side:.5},{'upper_leg.'+side:.25,'lower_leg.'+side:.75},{'lower_leg.'+side:1},{'lower_leg.'+side:1},{'lower_leg.'+side:1}]
        tube('TrousersJoint_'+side,legs,lr,'pants',ringweights=lw,n=24,flatten=.85)
        # Source-shaped glove scale; geometry authored in hand local coordinates.
        bone=rig.data.bones['hand.'+side]; mat=bone.matrix_local
        gl=[]
        palm=ellipsoid('GlovePalm_'+side,(.024,.026,0),(.026,.041,.043),'leather','hand.'+side); gl.append(palm)
        for j,z in enumerate([-.027,-.009,.009,.027]):
            points=[(.019*math.cos(t),.055+.019*math.sin(t),z) for t in [math.radians(-75+i*35) for i in range(9)]]
            gl.append(tube('GloveFinger%d_'%j+side,points,[.0075]*len(points),'leather','hand.'+side,n=10))
        gl.append(tube('GloveThumb_'+side,[(.037,.005,.028),(.030,.027,.040),(.012,.045,.036),(-.013,.054,.028)],[.010,.011,.010,.009],'leather','hand.'+side,n=12))
        for ob in gl:
            for v in ob.data.vertices: v.co=mat@v.co
            ob.data.update()
        # Cloth panels use a closed two-sided grid shell; separate bones, no fused legs.
        vs=[]; fs=[]; rows=10; cols=12
        for i in range(rows):
            t=i/(rows-1); z=.88-.46*t; rx=.207+.145*t; ry=.147+.07*t
            for j in range(cols):
                theta=s*(.48+(math.pi-.55-.48)*j/(cols-1)); fold=.006*math.cos(j*math.pi*2/3)*t
                vs.append((rx*math.sin(theta),-ry*math.cos(theta)+fold,z+.017*math.sin(theta)*t))
        for i in range(rows-1):
            for j in range(cols-1): fs.append((i*cols+j,i*cols+j+1,(i+1)*cols+j+1,(i+1)*cols+j))
        cloth=mesh('SplitCoat_'+side,vs,fs,'navy','coat.'+side); sol=cloth.modifiers.new('ClothThickness','SOLIDIFY'); sol.thickness=.006; sol.use_even_offset=True
        for js in [[0]+[i*cols for i in range(1,rows)],[(rows-1)*cols+j for j in range(cols)], [i*cols+cols-1 for i in range(rows)]]:
            tube('CoatSilverEdge_'+side+'_'+str(js[0]),[vs[j] for j in js],[.004]*len(js),'trim','coat.'+side,n=8)
    vs=[]; fs=[]; rows=9; cols=9
    for i in range(rows):
        t=i/(rows-1)
        for j in range(cols):
            u=(j/(cols-1)-.5)*2; vs.append((u*(.118-.020*t),-.153-.063*t-.007*math.cos(u*math.pi*2),.856-.425*t))
    for i in range(rows-1):
        for j in range(cols-1): fs.append((i*cols+j,i*cols+j+1,(i+1)*cols+j+1,(i+1)*cols+j))
    panel=mesh('IvoryFrontTabard',vs,fs,'ivory','pelvis'); sol=panel.modifiers.new('ClothThickness','SOLIDIFY'); sol.thickness=.005
    for edge in [[i*cols for i in range(rows)],[i*cols+cols-1 for i in range(rows)],[(rows-1)*cols+j for j in range(cols)]]:
        tube('IvoryHem_'+str(edge[0]),[vs[j] for j in edge],[.0025]*len(edge),'ivory','pelvis',n=8)
    # Independent actual blade, guard, grip, pommel and pelvis-mounted sheath.
    sx,sy,sz=REST['sword'][0]
    tube('SwordGrip',[(sx,sy,sz-.085),(sx,sy,sz+.055)],[.013,.013],'leather','sword',n=20)
    for z in [-.072,-.044,-.016,.012,.040]: tube('SwordGripBinding_'+str(z),[(sx,sy,sz+z),(sx,sy,sz+z+.005)],[.0137,.0137],'darkmetal','sword',n=16)
    tube('SwordGuard',[(sx-.10,sy,sz+.075),(sx-.075,sy,sz+.071),(sx+.075,sy,sz+.071),(sx+.10,sy,sz+.075)],[.014]*4,'gold','sword',n=12)
    ellipsoid('SwordPommel',(sx,sy,sz-.105),(.023,.018,.019),'gold','sword',n=16,rings=8)
    vs=[]
    for z,width in [(sz+.092,.026),(sz+.76,.019),(sz+.95,.0004)]: vs.extend([(sx-width,sy,z),(sx,sy-.006,z),(sx+width,sy,z),(sx,sy+.006,z)])
    fs=[(k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j) for k in range(2) for j in range(4)]+[(3,2,1,0),(8,9,10,11)]
    mesh('SwordBlade',vs,fs,'silver','sword')
    tube('EmptyScabbard',[(.21,.08,.875),(.28,.085,.60),(.35,.09,.295)],[.032,.029,.022],'leather','pelvis',n=16,flatten=.6)
    tube('ScabbardMouth',[(.21,.08,.865),(.213,.08,.885)],[.034,.034],'gold','pelvis',n=16,flatten=.6)
    bpy.data.objects.remove(original,do_unlink=True)
    if a.version=='v003':
        for ob in list(char.objects):
            if ob.type!='MESH': continue
            for modifier in list(ob.modifiers):
                if modifier.type=='SOLIDIFY':
                    bpy.context.view_layer.objects.active=ob; bpy.ops.object.modifier_apply(modifier=modifier.name)
    (QA/'source-selection.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'selections':source_selections,'face_skin_polygons':face_labels,'not_retained':['source hands','source waist/belt','source sword handle','source entire scabbard','source cloth tails','source trouser joints'],'method':'explicit planar source selection + authored quad-loop replacement; raw source unchanged'},indent=2)+'\n',encoding='utf-8')
    stage(); render_views(QA/'bind')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_repair_bind.blend'))
else:
    approval=QA/'preflight-review.json'
    if not approval.exists() or json.loads(approval.read_text())['decision']!='allow_full_animation': raise RuntimeError('Preflight review must precede full animation')
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'ro_repair_bind.blend'))
    rig=bpy.data.objects['ARM_RO_Swordsman']; char=bpy.data.collections['COL_Character']; effects=bpy.data.collections['COL_SkillEffects']

def pose(frame,target,key=False):
    _,hz,lean,yaw,rh,sd,lh,lf,rf=target; ym=Matrix.Rotation(yaw,3,'Z'); world=lambda v:ym@Vector(v)
    hz-=.03; hip=Vector((0,0,hz)); sp1=hip+world((0,0,.12)); sp2=sp1+world((0,lean*.38,.17)); neck=sp2+world((0,lean*.40,.19)); head=neck+world((0,0,.09))
    positions={'root':(Vector((0,0,0)),Vector((0,0,.18))),'pelvis':(hip,sp1),'spine_01':(sp1,sp2),'spine_02':(sp2,neck),'neck':(neck,head),'head':(head,head+world((0,0,.26)))}
    blade=world(sd).normalized(); normal=world((0,1,0)); right_dir=(blade.cross(normal)).normalized()
    # Continuous blade cross normal: a sign forced by global X flipped the
    # wrist by180degrees when the blade passed horizontal in the full stress.
    smooth=lambda t:(lambda u:u*u*(3-2*u))(max(0,min(1,t)))
    # Measured preflight found left fingertips25mm from handle at overhead.
    # Move the shared overhead grip toward the body centre within arm reach;
    # preserve the continuous ramp and original impact/landing targets.
    overhead_centre=smooth((frame-25)/20)*(1-smooth((frame-100)/20))
    # All-frame mesh/BVH inspection found blade/head overlap during wind-up
    # and apex. Centre the shared grip and move its arc ahead of the face.
    desired_grip=world(rh)+world((.22*overhead_centre,-.38*overhead_centre,0))
    actual_grip=None
    for side,s,foot in [('R',-1,rf),('L',1,lf)]:
        shoulder=neck+world((s*.24,0,-.04)); handdir=right_dir if side=='R' else -right_dir
        smooth=lambda t:(lambda u:u*u*(3-2*u))(max(0,min(1,t)))
        clasp=smooth((frame-25)/20)*(1-smooth((frame-125)/20))
        grip=desired_grip if side=='R' else world(lh).lerp(actual_grip-blade*.070,clasp)
        ht=grip-handdir*.055
        upper=(Vector(REST['upper_arm.'+side][1])-Vector(REST['upper_arm.'+side][0])).length
        lower=(Vector(REST['lower_arm.'+side][1])-Vector(REST['lower_arm.'+side][0])).length
        elbow,wrist=solve(shoulder,ht,upper,lower,world((s,1,-.2)))
        if side=='R': actual_grip=wrist+handdir*.055
        th=hip+world((s*.12,0,.02)); ft=Vector(foot); ft.z-=.03
        knee,ankle=solve(th,ft,(Vector(REST['upper_leg.'+side][1])-Vector(REST['upper_leg.'+side][0])).length,(Vector(REST['lower_leg.'+side][1])-Vector(REST['lower_leg.'+side][0])).length,Vector((0,-1,0)))
        toe=ankle+world((0,-.14,-.055))
        positions.update({'clavicle.'+side:(neck+world((0,0,-.04)),shoulder),'upper_arm.'+side:(shoulder,elbow),'lower_arm.'+side:(elbow,wrist),'hand.'+side:(wrist,wrist+handdir*.08),'upper_leg.'+side:(th,knee),'lower_leg.'+side:(knee,ankle),'foot.'+side:(ankle,toe),'toe.'+side:(toe,toe+world((0,-.06,0))),'coat.'+side:(hip+world((s*.13,.025,.01)),hip+world((s*(.23+.012*math.sin(frame*.045)),.04+.028*math.sin(frame*.055),-.37)))})
    positions['sword']=(actual_grip,actual_grip+blade*.95)
    matrices={}
    for name in REST:
        start,end=positions[name]
        reference=blade if name.startswith('hand.') else world(rig.data.bones[name].matrix_local.to_3x3().col[2])
        mat=bone_matrix(start,end,reference); mat.translation=start; matrices[name]=mat
        pb=rig.pose.bones[name]; parent=PARENTS[name]; rest=rig.data.bones[name].matrix_local
        pb.matrix_basis=rest.inverted()@rig.data.bones[parent].matrix_local@matrices[parent].inverted()@mat if parent else rest.inverted()@mat
        pb.rotation_mode='QUATERNION'
        if key:
            pb.keyframe_insert('location',frame=frame,group=name); pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
    bpy.context.view_layer.update()

if a.stage=='preflight':
    scene=bpy.context.scene; scene.render.resolution_x=scene.render.resolution_y=960
    for index,label in [(2,'overhead'),(5,'downslash'),(7,'landing')]:
        target=POSES[index]; pose(target[0],target)
        for view in ['front','three-quarter','side','back']:
            camera(view); scene.render.filepath=str(QA/'preflight'/f'{label}-{view}.png'); bpy.ops.render.render(write_still=True)
    print('RO_REBUILD_PREFLIGHT_DONE '+str(OUT/'ro_repair_bind.blend'))
else:
    for frame in range(1,301):
        for first,last in zip(POSES,POSES[1:]):
            if first[0]<=frame<=last[0]:
                t=(frame-first[0])/(last[0]-first[0]); t=t*t*(3-2*t)
                target=[frame]+[first[i]+(last[i]-first[i])*t if isinstance(first[i],(int,float)) else tuple(Vector(first[i]).lerp(Vector(last[i]),t)) for i in range(1,len(first))]
                pose(frame,target,key=True); break
    rig.animation_data.action.name='AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory'
    for fc in rig.animation_data.action.fcurves:
        for key in fc.keyframe_points: key.interpolation='LINEAR'
    scene=bpy.context.scene
    for name,f in [('Provoke',1),('Bash',50),('MagnumBreak',145),('Endure',235),('Victory',280)]: scene.timeline_markers.new(name,frame=f)
    # Separate reversible presentation effects; never part of body mesh or gameplay.
    effect_materials={
        'slash':material('FX_SlashIvory',(.50,.72,.88),rough=.35,emission=3),
        'fire':material('FX_FireOrange',(.85,.10,.008),rough=.55,emission=4),
        'hot':material('FX_FireGold',(.95,.38,.025),rough=.5,emission=5),
        'endure':material('FX_EndureGold',(.80,.48,.07),rough=.35,emission=3)}
    def effect(name,vertices,faces,mat,start,peak,end):
        data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
        ob=bpy.data.objects.new('FX_'+name,data);effects.objects.link(ob);data.materials.append(effect_materials[mat])
        for f,value in [(1,.00001),(start-1,.00001),(start,.00001),(peak,1),(end,.00001),(300,.00001)]:
            ob.scale=(value,)*3;ob.keyframe_insert('scale',frame=f)
        ob.animation_data.action.name='FX_'+name
        for fc in ob.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
        return ob
    def ribbon(name,center,ra,rb,plane,mat,start,peak,end,angle=(0,math.tau)):
        vs=[];fs=[];n=72
        for j in range(n+1):
            t=j/n;q=angle[0]+t*(angle[1]-angle[0]);width=.012*max(.1,math.sin(t*math.pi))
            for d in [-width,width]:
                v=(Vector((0,(ra+d)*math.cos(q),(rb+d)*math.sin(q))) if plane=='YZ' else Vector(((ra+d)*math.cos(q),0,(rb+d)*math.sin(q))) if plane=='XZ' else Vector(((ra+d)*math.cos(q),(rb+d)*math.sin(q),0)))
                vs.append(Vector(center)+v)
            if j<n:fs.append((j*2,j*2+1,j*2+3,j*2+2))
        return effect(name,vs,fs,mat,start,peak,end)
    ribbon('BashArc',(0,-.15,1.05),1.22,.98,'XZ','slash',105,119,136,angle=(math.radians(10),math.radians(205)))
    ribbon('MagnumGroundRing',(0,0,.035),.84,.84,'XY','hot',191,211,226)
    for j in range(18):
        q=j*math.tau/18;rad=.60+.10*math.sin(j*1.7);cent=Vector((rad*math.cos(q),rad*math.sin(q),.03));vs=[];fs=[];n=10
        for i in range(5):
            t=i/4;radius=.11*(1-t)+.006;z=t*(.48+.20*math.sin(j*2.3));bend=Vector((math.cos(q)*.18*t*t,math.sin(q)*.18*t*t,z))
            for k in range(n):vs.append(cent+bend+Vector((radius*math.cos(k*math.tau/n),radius*math.sin(k*math.tau/n),.02*math.sin(k*math.tau/n)*t)))
        for i in range(4):
            for k in range(n):fs.append((i*n+k,i*n+(k+1)%n,(i+1)*n+(k+1)%n,(i+1)*n+k))
        fs.extend([tuple(reversed(range(n))),tuple(range(4*n,5*n))]);effect('MagnumFlame%02d'%j,vs,fs,'fire' if j%2 else 'hot',190+j%4,209+j%3,230)
    ribbon('EndureHaloFront',(0,0,.98),.68,1.02,'XZ','endure',225,238,265)
    ribbon('EndureHaloSide',(0,0,.98),.68,1.02,'YZ','endure',225,238,265)
    ribbon('EndureGround',(0,0,.02),.61,.61,'XY','endure',225,238,265)
    effects.hide_render=True
    scene.frame_set(1); render_views(QA)
    scene.render.resolution_x=scene.render.resolution_y=640
    for f in [1,25,50,75,100,120,145,170,195,220,255,300]:
        scene.frame_set(f); camera(); scene.render.filepath=str(QA/f'pose_{f:04d}.png'); bpy.ops.render.render(write_still=True)
    effects.hide_render=False
    for f in [120,211,240]:
        scene.frame_set(f);camera(((2.8,-4,2),(0,0,1.1),3.3));scene.render.filepath=str(QA/f'effects_{f:04d}.png');bpy.ops.render.render(write_still=True)
    scene.frame_set(1); camera(); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_swordsman_master.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in char.objects: ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_swordsman_combo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_yup=True,export_anim_slide_to_zero=True,export_skins=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in effects.objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=next(iter(effects.objects))
    bpy.ops.export_scene.gltf(filepath=str(OUT/'ro_skill_effects.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_yup=True,export_anim_slide_to_zero=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
    report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'master':str((OUT/'ro_swordsman_master.blend').relative_to(ROOT)),'source_bind_sha256':hashlib.sha256((OUT/'ro_repair_bind.blend').read_bytes()).hexdigest(),'triangles_character':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in char.objects if ob.type=='MESH'),'triangles_effects':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in effects.objects if ob.type=='MESH'),'bones':len(rig.data.bones),'frames':300,'fps':60,'effects_collection':'COL_SkillEffects','effects_separate_glb':True,'art_acceptance':'not_run','continuous_acceptance':'not_run'}
    (QA/'construction-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('RO_REBUILD_FULL_DONE '+str(OUT/'ro_swordsman_combo.glb'))
