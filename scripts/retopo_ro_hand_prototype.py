"""Bounded right-hand source-guided cage, wrist seam and actual deformation prototype."""
from collections import Counter
from datetime import datetime,timezone
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import curl_digits,pose
from ro_review_common import camera
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v003-hand-prototype'
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-prototype'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-digit-weights/weights.json').read_text())
source=ROOT/previous['artifact']['path']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if OUT.exists() or QA.exists() or sha(source)!=previous['artifact']['sha256']: raise RuntimeError('Preserve sources and previous prototype')
start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v003-start.json').read_text()); phase=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
def guard():
    now=datetime.now(timezone.utc)
    if (now-datetime.fromisoformat(start['started_utc'])).total_seconds()>=start['prototype_deadline_seconds'] or (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds']: raise RuntimeError('Original prototype/phase budget exhausted')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; sword=bpy.data.objects['SM_RO_sword']; state=json.loads(rig['state_json']); original=copy.deepcopy(state)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
core.data.calc_loop_triangles()
points=[v.co.copy() for v in core.data.vertices]
triangles=[list(t.vertices) for t in core.data.loop_triangles]
triangle_uv=[[core.data.uv_layers.active.data[i].uv.copy() for i in t.loops] for t in core.data.loop_triangles]
tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
def transferred_uv(p):
    hit,normal,index,d=tree.find_nearest(p)
    a,b,c=(points[i] for i in triangles[index]); v0=b-a; v1=c-a; v2=hit-a
    d00=v0.dot(v0); d01=v0.dot(v1); d11=v1.dot(v1); d20=v2.dot(v0); d21=v2.dot(v1); den=d00*d11-d01*d01
    if abs(den)<1e-15: return triangle_uv[index][0]
    v=(d11*d20-d01*d21)/den; w=(d00*d21-d01*d20)/den
    return triangle_uv[index][0]*(1-v-w)+triangle_uv[index][1]*v+triangle_uv[index][2]*w
def protected_faces():
    result=[]
    uv=core.data.uv_layers.active.data
    for f in core.data.polygons:
        if any(core.data.vertices[i].co.x<-.34 and core.data.vertices[i].co.z<.926 for i in f.vertices): continue
        result.append(tuple(sorted((tuple(round(v,7) for v in core.data.vertices[i].co),tuple(round(v,7) for v in uv[j].uv)) for i,j in zip(f.vertices,f.loop_indices))))
    return Counter(result)
protected=protected_faces()
side='R'; sign=-1; knuckles=[Vector(p) for p in state['measurements'][side]['knuckles']]; tips=[Vector(p) for p in state['measurements'][side]['tips']]
down=sum(((t-h).normalized() for h,t in zip(knuckles,tips)),Vector()).normalized(); width=knuckles[-1]-knuckles[0]
if width.x<0: width=-width
width=(width-down*width.dot(down)).normalized(); front=down.cross(width).normalized()
state['hand_frames'][side]={'width':list(width),'front':list(front),'down':list(down),'determinant':Matrix((width,front,down)).transposed().determinant(),'down_method':'mean normalized per-finger measured directions'}

# Clip only the right glove below z=.923; original body/head/left hand remain untouched.
bm=bmesh.new(); bm.from_mesh(core.data); bm.verts.ensure_lookup_table()
geom=[v for v in bm.verts if v.co.x<-.34 and v.co.z<.98]
geom += [e for e in bm.edges if all(v.co.x<-.34 and v.co.z<.98 for v in e.verts)]
geom += [f for f in bm.faces if all(v.co.x<-.34 and v.co.z<.98 for v in f.verts)]
bmesh.ops.bisect_plane(bm,geom=geom,dist=1e-7,plane_co=Vector((0,0,.923)),plane_no=Vector((0,0,1)),clear_inner=True,clear_outer=False)
discard=[v for v in bm.verts if v.co.x<-.34 and v.co.z<.923-1e-6]
if discard: bmesh.ops.delete(bm,geom=discard,context='VERTS')
boundary=[e for e in bm.edges if e.is_boundary and all(v.co.x<-.34 and abs(v.co.z-.923)<1e-5 for v in e.verts)]
if not 10<=len(boundary)<=60: raise RuntimeError('Unexpected right wrist seam')
start_v=boundary[0].verts[0]; loop=[start_v]; current=start_v; last=None
while True:
    edges=[e for e in current.link_edges if e in boundary and e!=last]
    if not edges: raise RuntimeError('Open cut loop')
    edge=edges[0]; other=edge.other_vert(current)
    if other==start_v: break
    loop.append(other); current=other; last=edge
    if len(loop)>len(boundary): raise RuntimeError('Invalid seam cycle')
if len(loop)!=len(boundary): raise RuntimeError('Multiple wrist loops')
cut_center=sum((v.co for v in loop),Vector())/len(loop)

group_names=list(state['rest'])+[f'finger{i}.R_03' for i in range(1,5)]
for name in group_names:
    if not core.vertex_groups.get(name): core.vertex_groups.new(name=name)
deform=bm.verts.layers.deform.verify(); uv_layer=bm.loops.layers.uv.verify(); newverts=[]; newfaces=[]; semantic={}; pads={}
def vertex(p,weights):
    v=bm.verts.new(p); newverts.append(v); total=sum(weights.values())
    for n,w in weights.items():
        if w>1e-8: v[deform][core.vertex_groups[n].index]=w/total
    return v
def face(vs):
    f=bm.faces.new(vs); f.material_index=0; f.smooth=True; newfaces.append(f)
    for l in f.loops: l[uv_layer].uv=transferred_uv(l.vert.co)
    return f
def joint_weights(branch,s,middle=.40,distal=.70):
    hand=max(0,min(1,(.15-s)/.30)); w2=max(0,min(1,(s-middle+.09)/.18)); w3=max(0,min(1,(s-distal+.09)/.18))
    return {'hand.R':hand,branch+'.R_01':(1-hand)*(1-w2),branch+'.R_02':(1-hand)*w2*(1-w3),branch+'.R_03':(1-hand)*w3}
root_radius=[]
for i,h in enumerate(knuckles):
    spacing=min((h-other).length for j,other in enumerate(knuckles) if i!=j)
    root_radius.append(min(.010,spacing*.40))
# Palm front/back cage with independent finger ports and finite webs between them.
xs=[]; ys=[]
for h,r in zip(knuckles,root_radius):
    for a in (-1,0,1): xs.append(h.x+a*r); ys.append(h.y)
order=sorted(range(12),key=lambda i:xs[i]); xs=[xs[i] for i in order]; ys=[ys[i] for i in order]
rows=[.926,.906,.886,.867]; grids={}; mids={}
for k,z in enumerate(rows):
    blend=(rows[0]-z)/(rows[0]-rows[-1]); center_x=cut_center.x*(1-blend)+sum(h.x for h in knuckles)/4*blend
    for surface,direction in [('front',-1),('back',1)]:
        row=[]
        for j,(x,y) in enumerate(zip(xs,ys)):
            width_scale=.54+.46*blend; px=center_x+(x-sum(h.x for h in knuckles)/4)*width_scale
            py=cut_center.y*(1-blend)+y*blend+direction*(.016*(1-blend)+.010*blend)
            weights={'hand.R':1}
            if k==3:
                finger=order[j]//3+1; weights={'hand.R':.5,f'finger{finger}.R_01':.5}
            row.append(vertex(Vector((px,py,z)),weights))
        grids[(surface,k)]=row
    for end in [0,11]:
        a=grids[('front',k)][end]; b=grids[('back',k)][end]; mids[(end,k)]=vertex(a.co.lerp(b.co,.5),{'hand.R':1})
for surface in ['front','back']:
    for k in range(3):
        for j in range(11): face([grids[(surface,k)][j],grids[(surface,k)][j+1],grids[(surface,k+1)][j+1],grids[(surface,k+1)][j]])
# Thumb port is two adjacent outer side quads; the inner side stays intact.
outer=0
for end in [0,11]:
    for k in range(3):
        if end==outer and k==1: continue
        face([grids[('front',k)][end],mids[(end,k)],mids[(end,k+1)],grids[('front',k+1)][end]])
        face([mids[(end,k)],grids[('back',k)][end],grids[('back',k+1)][end],mids[(end,k+1)]])
top=grids[('front',0)]+[mids[(11,0)]]+list(reversed(grids[('back',0)]))+[mids[(0,0)]]
def cyclic_sorted(vs,center): return sorted(vs,key=lambda v:math.atan2(v.co.y-center.y,v.co.x-center.x))
a=cyclic_sorted(loop,cut_center); b=cyclic_sorted(top,cut_center)
# Unequal seam zipper: topology changes stay at the non-bending cuff.
i=j=0
while i<len(a) or j<len(b):
    if i<len(a) and j<len(b) and abs((i+1)/len(a)-(j+1)/len(b))<1e-8:
        face([a[i%len(a)],a[(i+1)%len(a)],b[(j+1)%len(b)],b[j%len(b)]]); i+=1; j+=1
    elif j==len(b) or i<len(a) and (i+1)/len(a)<(j+1)/len(b):
        face([a[i%len(a)],a[(i+1)%len(a)],b[j%len(b)]]); i+=1
    else:
        face([a[i%len(a)],b[(j+1)%len(b)],b[j%len(b)]]); j+=1

new_bones={}
finger_ports={}; web_mids={}
for finger,h in enumerate(knuckles,1):
    js=[order.index((finger-1)*3+c) for c in range(3)]; js.sort(); left,mid,right=js
    lmid=mids[(0,3)] if left==0 else vertex(grids[('front',3)][left].co.lerp(grids[('back',3)][left].co,.5),{'hand.R':.5,f'finger{finger}.R_01':.5})
    rmid=mids[(11,3)] if right==11 else vertex(grids[('front',3)][right].co.lerp(grids[('back',3)][right].co,.5),{'hand.R':.5,f'finger{finger}.R_01':.5})
    port=[grids[('front',3)][left],grids[('front',3)][mid],grids[('front',3)][right],rmid,grids[('back',3)][right],grids[('back',3)][mid],grids[('back',3)][left],lmid]
    finger_ports[finger]=port; web_mids[left]=lmid; web_mids[right]=rmid
for j in [2,5,8]:
    face([grids[('front',3)][j],grids[('front',3)][j+1],web_mids[j+1],web_mids[j]])
    face([web_mids[j],web_mids[j+1],grids[('back',3)][j+1],grids[('back',3)][j]])
levels=[0,.25,.40,.54,.70,.86,.97]
for finger,(h,t) in enumerate(zip(knuckles,tips),1):
    branch='finger'+str(finger); direction=(t-h).normalized(); cross=direction.cross(front).normalized(); normal=cross.cross(direction).normalized()
    if normal.dot(front)<0: normal=-normal
    port=finger_ports[finger]; last=port; pads[branch]=[]
    # Port order follows front-left to front-right/back-right. Corresponding ellipse angles.
    basis=[(-1,0),(-.707,1),(0,1),(.707,1),(1,0),(.707,-1),(0,-1),(-.707,-1)]
    # Use the actual port radial directions to preserve loop correspondence, not a twisted template.
    radials=[]
    for v in port:
        d=v.co-h; radial=Vector((d.dot(cross),d.dot(normal))); radials.append(radial.normalized())
    for s in levels[1:]:
        center=h.lerp(t,s); taper=1-.40*max(0,(s-.70)/.30); rw=root_radius[finger-1]*taper; rd=.010*taper
        ring=[]
        for q,radial in enumerate(radials):
            p=center+cross*radial.x*rw+normal*radial.y*rd
            v=vertex(p,joint_weights(branch,s)); semantic[v]=branch
            if radial.y>.45 and .25<=s<=.86: pads[branch].append(v)
            ring.append(v)
        for q in range(8): face([last[q],last[(q+1)%8],ring[(q+1)%8],ring[q]])
        last=ring
    cap=vertex(t, {branch+'.R_03':1}); semantic[cap]=branch
    for q in range(8): face([last[q],last[(q+1)%8],cap])
    new_bones[branch+'.R_01']=(h,h.lerp(t,.40)); new_bones[branch+'.R_02']=(h.lerp(t,.40),h.lerp(t,.70)); new_bones[branch+'.R_03']=(h.lerp(t,.70),t)

# Thumb: retain a separate two-joint opposition chain and its source direction.
port=[grids[('front',1)][outer],mids[(outer,1)],grids[('back',1)][outer],grids[('back',2)][outer],mids[(outer,2)],grids[('front',2)][outer]]
h=sum((v.co for v in port),Vector())/6; t=Vector(state['measurements']['R']['thumb_tip']); m=h.lerp(t,.52)
axis=(t-h).normalized(); ref=Vector((0,0,1)); u=axis.cross(ref).normalized(); vaxis=u.cross(axis).normalized()
radials=[Vector(((v.co-h).dot(u),(v.co-h).dot(vaxis))).normalized() for v in port]; last=port; pads['thumb']=[]
for s in [.20,.38,.52,.68,.85,.97]:
    ring=[]; blend=max(0,min(1,(s-.43)/.18)); hand=max(0,min(1,(.18-s)/.36))
    for radial in radials:
        p=h.lerp(t,s)+(u*radial.x+vaxis*radial.y)*(.011*(1-.40*max(0,(s-.7)/.3)))
        v=vertex(p,{'hand.R':hand,'thumb.R_01':(1-hand)*(1-blend),'thumb.R_02':(1-hand)*blend}); semantic[v]='thumb'; pads['thumb'].append(v); ring.append(v)
    for q in range(6): face([last[q],last[(q+1)%6],ring[(q+1)%6],ring[q]])
    last=ring
cap=vertex(t,{'thumb.R_02':1}); semantic[cap]='thumb'
for q in range(6): face([last[q],last[(q+1)%6],cap])
new_bones['thumb.R_01']=(h,m); new_bones['thumb.R_02']=(m,t)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.verts.index_update(); bm.faces.index_update()
bad=[e for e in bm.edges if not e.is_manifold]
if bad: raise RuntimeError('Retopology nonmanifold edges: '+str(len(bad)))
regions={v.index:part for v,part in semantic.items()}; pad_ids={n:[v.index for v in vs] for n,vs in pads.items()}
generated_triangles=sum(len(f.verts)-2 for f in newfaces); seam_count=len(loop)
bm.to_mesh(core.data); bm.free(); core.data.update()
if protected!=protected_faces(): raise RuntimeError('Protected body/UV faces changed')
whole_triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.data.collections['COL_Character'].objects if o.type=='MESH')
if whole_triangles>60000: raise RuntimeError('Whole character exceeds60000tri: '+str(whole_triangles))
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
for name,(h,t) in new_bones.items():
    bone=rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name); bone.head=h; bone.tail=t
    if name.endswith('_03'): bone.parent=rig.data.edit_bones[name[:-2]+'02']; state['parents'][name]=name[:-2]+'02'
    state['rest'][name]=[list(h),list(t)]
bpy.ops.object.mode_set(mode='OBJECT')
# Parent-before-child order for the extra distal joints.
ordered={}
while len(ordered)<len(state['rest']):
    for n,segment in state['rest'].items():
        if n not in ordered and (state['parents'][n] is None or state['parents'][n] in ordered): ordered[n]=segment
state['rest']=ordered; state.setdefault('finger_joint_count',{})['R']=3
state['finger_angles']['R']={str(i):[.95,1.40,.85] for i in range(1,5)}
state['thumb_offsets']['R']=[-.030,.009,-.020]
palm=sum(knuckles,Vector())/4
state['grips']['R']=list(palm+front*.031+down*(-.008))
new_axis=-width; origin=Vector(state['grips']['R']); rotation=Vector(original['weapon_axis_in_rest']).rotation_difference(new_axis).to_matrix()
for vertex_data in sword.data.vertices: vertex_data.co=origin+rotation@(vertex_data.co-Vector(original['grips']['R']))
sword.data.update()
bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT'); bone=rig.data.edit_bones['sword']; bone.head=origin; bone.tail=origin+new_axis*.8; bpy.ops.object.mode_set(mode='OBJECT')
state['rest']['sword']=[list(origin),list(origin+new_axis*.8)]; state['weapon_axis_in_rest']=list(new_axis)
state['retopology_regions']={'R':regions}; state['contact_pad_vertices']={'R':pad_ids}; rig['state_json']=json.dumps(state)
OUT.mkdir(parents=True); QA.mkdir(parents=True)
(QA/'rig-helper-used.py').write_bytes((ROOT/'scripts/ro_core_rig.py').read_bytes())
def views(folder):
    folder.mkdir(parents=True,exist_ok=True)
    hidden=[]
    for ob in bpy.data.collections['COL_Character'].objects:
        if ob.type=='MESH' and ob not in (core,sword): hidden.append((ob,ob.hide_render)); ob.hide_render=True
    target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.65)
    for name,offset in [('front',(.30,-1,.15)),('side',(1,0,.12)),('back',(-.3,1,.12))]:
        camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
    for ob,hidden_value in hidden: ob.hide_render=hidden_value
views(QA/'open')
small=copy.deepcopy(state); small['finger_angles'].pop('R',None); curl_digits(rig,small,'R',.30); views(QA/'small-curl')
result=pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),two_hands=False); views(QA/'single-grip')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_hand_prototype.blend'))
report={'trial':'v003','stage':'right hand prototype, manual view gate pending','source':previous['artifact'],'source_preserved':sha(source)==previous['artifact']['sha256'],
    'method':'Source-guided palm front/back quad cage, four independent eight-sided joint-loop fingers, finite webs, two-joint thumb port and unequal wrist seam bridge. Nearest original triangle UV barycentric transfer; no body/head edits.',
    'right_wrist_cut_z':.923,'wrist_seam_edges':seam_count,'new_region_triangles':generated_triangles,'whole_character_triangles':whole_triangles,'nonmanifold_edges':0,'protected_geometry_and_uv_unchanged':True,
    'bones':len(rig.data.bones),'right_finger_joints':3,'source_grip_search_count':100,'new_numerical_search_evaluations':0,'single_pose':result,'art_accepted':False,'rig_accepted':False,
    'artifact':{'path':(OUT/'ro_hand_prototype.blend').relative_to(ROOT).as_posix(),'sha256':sha(OUT/'ro_hand_prototype.blend')}}
(QA/'prototype.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_HAND_PROTOTYPE '+json.dumps(report))
