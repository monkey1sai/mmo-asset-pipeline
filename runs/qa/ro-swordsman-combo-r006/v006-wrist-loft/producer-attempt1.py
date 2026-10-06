"""v006 protect semantic hand vertices; loft real cut rings, then trim bracer."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_core_rig import assign
from ro_hand_gate import contacts,evaluated,segment_hit
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v006-wrist-loft'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v006-wrist-loft'
start=json.loads((BASEQA/'v006-start.json').read_text()); clock=json.loads((BASEQA/'phase-start.json').read_text()); source=ROOT/start['source']['path']
assert not QA.exists() and not OUT.exists(); assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
def save(name,value): (QA/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False); QA.mkdir(parents=True); OUT.mkdir(parents=True)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; glove=bpy.data.objects['SM_RO_glove.R']; bracer=bpy.data.objects['SM_RO_bracer.R']; sword=bpy.data.objects['SM_RO_sword']
state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); oldpads=json.loads(glove['fixed_pad_indices'])
old=bpy.data.objects.get('SM_RO_WristSleeve.R')
if old: bpy.data.objects.remove(old,do_unlink=True)
wrist=Vector(state['rest']['hand.R'][0]); axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized()
anatomy=json.loads((BASEQA/'v001-generated-glove/anatomy-and-masks.json').read_text()); rotation=Matrix(anatomy['rotation']); source_wrist=Vector(anatomy['source_wrist'])
cut_z=.046
original=glove.data; original.calc_loop_triangles(); oldbasis=[p.co.copy() for p in original.shape_keys.key_blocks['Basis'].data]; oldkey=[p.co.copy() for p in original.shape_keys.key_blocks['GripContact_R'].data]
oldweights=[{glove.vertex_groups[g.group].name:g.weight for g in v.groups} for v in original.vertices]
distances=[(rotation.inverted()@(p-wrist)+source_wrist).z-cut_z for p in oldbasis]
kept={i:i2 for i2,i in enumerate(i for i,d in enumerate(distances) if d>=-1e-9)}
verts=[oldbasis[i] for i in kept]; shapes=[oldkey[i] for i in kept]; weights=[oldweights[i] for i in kept]; faces=[]; uvs=[]; mats=[]; edge_new={}
def crossing(i,j):
    e=tuple(sorted([i,j]))
    if e not in edge_new:
        t=distances[i]/(distances[i]-distances[j]); ident=len(verts); edge_new[e]=ident
        verts.append(oldbasis[i].lerp(oldbasis[j],t)); shapes.append(oldkey[i].lerp(oldkey[j],t))
        values={n:oldweights[i].get(n,0)*(1-t)+oldweights[j].get(n,0)*t for n in set(oldweights[i])|set(oldweights[j])}; total=sum(values.values())
        weights.append({n:w/total for n,w in values.items() if w>1e-8})
    return edge_new[e]
protected_uv=[]
for tri in original.loop_triangles:
    rows=[(int(i),Vector(original.uv_layers.active.data[l].uv)) for i,l in zip(tri.vertices,tri.loops)]; result=[]
    for k,(i,uv) in enumerate(rows):
        j,uvj=rows[(k+1)%3]; a=distances[i]>=-1e-9; b=distances[j]>=-1e-9
        if a: result.append((kept[i],uv))
        if a!=b:
            t=distances[i]/(distances[i]-distances[j]); result.append((crossing(i,j),uv.lerp(uvj,t)))
    for k in range(1,len(result)-1):
        selected=[result[i] for i in [0,k,k+1]]; faces.append([i for i,uv in selected]); uvs.append([list(uv) for i,uv in selected]); mats.append(tri.material_index)
    if all(distances[i]>=-1e-9 for i,uv in rows): protected_uv.append({'old_triangle':list(tri.vertices),'uv':[list(uv) for i,uv in rows]})
mesh=bpy.data.meshes.new('RO_RightGlove_ProtectedCut'); mesh.from_pydata(verts,[],faces); mesh.update(); glove.data=mesh
for mat in original.materials: mesh.materials.append(mat)
uvlayer=mesh.uv_layers.new(name='UVMap')
for p,uvs_row,mat in zip(mesh.polygons,uvs,mats):
    p.material_index=mat; p.use_smooth=True
    for l,uv in zip(p.loop_indices,uvs_row): uvlayer.data[l].uv=uv
glove.shape_key_add(name='Basis'); key=glove.shape_key_add(name='GripContact_R')
for p,co in zip(key.data,shapes): p.co=co
for v,w in zip(mesh.vertices,weights): assign(glove,v,w)
pads={n:[kept[i] for i in ids] for n,ids in oldpads.items()}; glove['fixed_pad_indices']=json.dumps(pads)
assert all(len(ids)==len(oldpads[n]) for n,ids in pads.items())
assert all((mesh.vertices[kept[i]].co-oldbasis[i]).length<1e-8 and (key.data[kept[i]].co-oldkey[i]).length<1e-8 for i in kept)
save('semantic-cut-map.json',{'original_to_new':kept,'new_edge_vertices':{str(e):i for e,i in edge_new.items()},'pads_before':oldpads,'pads_after':pads,
    'cut_source_z_m':cut_z,'protected_kept_vertices':len(kept),'protected_uv_triangles':len(protected_uv),'source_faces':len(original.polygons),'cut_faces':len(mesh.polygons),
    'protected_basis_max_delta_m':0,'protected_contact_shape_max_delta_m':0,'protected_weights_changed':False,
    'protected_uv_sha256':hashlib.sha256(json.dumps(protected_uv,sort_keys=True).encode()).hexdigest(),'mask_frozen_before_new_replay':True})

def ordered_loop(ob,glove_loop=False):
    bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    boundary=[e for e in bm.edges if e.is_boundary]; assert boundary
    adjacency={v:set() for e in boundary for v in e.verts}
    for e in boundary:
        a,b=e.verts; adjacency[a].add(b); adjacency[b].add(a)
    assert all(len(a)==2 for a in adjacency.values()),'Actual boundary is not one simple ring'
    v0=min(adjacency,key=lambda v:(v.co.x,v.co.y,v.co.z)); path=[v0]; previous=None; current=v0
    while True:
        nxt=next(v for v in adjacency[current] if v!=previous)
        if nxt==v0: break
        assert nxt not in path; path.append(nxt); previous,current=current,nxt
    assert len(path)==len(adjacency),'Multiple boundary components need independent diagnosis'
    points=[v.co.copy() for v in path]; bm.free()
    indexes=[]; boneweights=[]
    for p in points:
        i=min(range(len(ob.data.vertices)),key=lambda i:(ob.data.vertices[i].co-p).length_squared); assert (ob.data.vertices[i].co-p).length<2e-6
        indexes.append(i); boneweights.append({ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[i].groups})
    return points,boneweights,indexes
gp,gw,gi=ordered_loop(glove,True); cp,cw,ci=ordered_loop(core)
width=Vector(state['hand_frames']['R']['width']); u=(width-axis*axis.dot(width)).normalized(); v=axis.cross(u).normalized()
def winding(points): return sum((a-wrist).dot(u)*(b-wrist).dot(v)-(b-wrist).dot(u)*(a-wrist).dot(v) for a,b in zip(points,points[1:]+points[:1]))
if winding(cp)*winding(gp)<0: cp.reverse(); cw.reverse(); ci.reverse()
# Rotate, never sort, the actual connected loop to the nearest anatomical phase.
centerg=sum(gp,Vector())/len(gp); centerc=sum(cp,Vector())/len(cp); gdir=(gp[0]-centerg).normalized()
anchor=max(range(len(cp)),key=lambda i:(cp[i]-centerc).normalized().dot(gdir)); cp=cp[anchor:]+cp[:anchor]; cw=cw[anchor:]+cw[:anchor]; ci=ci[anchor:]+ci[:anchor]
def fractions(points):
    lengths=[(b-a).length for a,b in zip(points,points[1:]+points[:1])]; perimeter=sum(lengths); acc=[0]
    for length in lengths: acc.append(acc[-1]+length/perimeter)
    return acc,perimeter
def resample(points,n):
    q,_=fractions(points); out=[]
    for i in range(n):
        t=i/n; j=next(j for j in range(len(points)) if q[j]<=t<=q[j+1]); out.append(points[j].lerp(points[(j+1)%len(points)],(t-q[j])/(q[j+1]-q[j])))
    return out
N=48; cr=resample(cp,N); gr=resample(gp,N); rings=[cp]
for t in [.25,.5,.75]: rings.append([a.lerp(b,t) for a,b in zip(cr,gr)])
rings.append(gp); tv=[]; ranges=[]
for ring in rings: ranges.append(list(range(len(tv),len(tv)+len(ring)))); tv.extend(ring)
tf=[]; tuv=[]
for row in range(4):
    a,b=rings[row:row+2]; fa,_=fractions(a); fb,_=fractions(b); i=j=0
    while i<len(a) or j<len(b):
        ia=i%len(a); jb=j%len(b); ai=ranges[row][ia]; bj=ranges[row+1][jb]
        if i<len(a) and j<len(b) and abs(fa[i+1]-fb[j+1])<1e-8:
            tf.append([ai,ranges[row][(i+1)%len(a)],ranges[row+1][(j+1)%len(b)],bj]); tuv.append([(fa[i],row/4),(fa[i+1],row/4),(fb[j+1],(row+1)/4),(fb[j],(row+1)/4)]); i+=1; j+=1
        elif i<len(a) and (j==len(b) or fa[i+1]<fb[j+1]):
            tf.append([ai,ranges[row][(i+1)%len(a)],bj]); tuv.append([(fa[i],row/4),(fa[i+1],row/4),(fb[j],(row+1)/4)]); i+=1
        else:
            tf.append([ai,ranges[row+1][(j+1)%len(b)],bj]); tuv.append([(fa[i],row/4),(fb[j+1],(row+1)/4),(fb[j],(row+1)/4)]); j+=1
tm=bpy.data.meshes.new('RO_WristLoft_R'); tm.from_pydata(tv,[],tf); tm.update(); tube=bpy.data.objects.new('SM_RO_WristLoft.R',tm); bpy.data.collections['COL_Character'].objects.link(tube)
uv=tm.uv_layers.new(name='UVMap')
for p,row in zip(tm.polygons,tuv):
    p.use_smooth=True
    for l,co in zip(p.loop_indices,row): uv.data[l].uv=(.02+.96*co[0],.02+.96*co[1])
mat=bpy.data.materials.new('M_RO_WristLeather'); mat.use_nodes=True; bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(.13,.065,.035,1); bs.inputs['Roughness'].default_value=.7; tm.materials.append(mat)
# Additional deform bone is rest-relative, evaluated explicitly in every replay.
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
bone=rig.data.edit_bones.new('wrist_transition.R'); bone.head=wrist; bone.tail=wrist+Vector(state['hand_frames']['R']['down'])*.04; bone.parent=rig.data.edit_bones['lower_arm.R']; bpy.ops.object.mode_set(mode='OBJECT')
state['rest']['wrist_transition.R']=[list(bone.head) if False else list(wrist),list(wrist+Vector(state['hand_frames']['R']['down'])*.04)]; state['parents']['wrist_transition.R']='lower_arm.R'; rig['state_json']=json.dumps(state)
for row,ids in enumerate(ranges):
    for i,index in enumerate(ids):
        if row==0: w=cw[i]
        elif row==4: w=gw[i]
        elif row==1: w={'lower_arm.R':.5,'wrist_transition.R':.5}
        elif row==2: w={'wrist_transition.R':1}
        else: w={'wrist_transition.R':.5,'hand.R':.5}
        assign(tube,tm.vertices[index],w)
mod=tube.modifiers.new('Armature','ARMATURE'); mod.object=rig; tube.parent=rig
rest_edges=[(e.index,(tm.vertices[e.vertices[0]].co-tm.vertices[e.vertices[1]].co).length) for e in tm.edges]
save('ring-loft.json',{'core_boundary_vertices':len(cp),'glove_boundary_vertices':len(gp),'middle_rings':3,'middle_vertices_per_ring':48,
 'loop_order':'actual edge connectivity; winding agreed, cyclic anatomical phase anchor, cumulative edge arclength zipper',
 'core_perimeter_m':fractions(cp)[1],'glove_perimeter_m':fractions(gp)[1],'new_vertices':len(tv),'new_faces':len(tf),
 'core_boundary_indices':ci,'glove_boundary_indices':gi,'new_uv':'one explicit rectangular circumference/axial island with .02margin; own brown leather material',
 'core_rest_seam_max_gap_m':0,'glove_rest_seam_max_gap_m':0,'documented_open_boundary':'tube/core and tube/glove geometrically matched separate-object rings; no center-fan closure'})

events=[]
def event(label):
    guard(); key.value=1; configure(rig,state,params); r=contacts(glove,sword,rig,pads,'single-grip',{'joint_ik':params,'checkpoint':label})
    r.update(event_kind=label,event_number=len(events)+1,timestamp_utc=datetime.now(timezone.utc).isoformat()); events.append(r); save('contact-events.json',events); return r
def intersections(aob,bob):
    ap,at,_=evaluated(aob); bp,bt,_=evaluated(bob); a=BVHTree.FromPolygons(ap,at,all_triangles=True); b=BVHTree.FromPolygons(bp,bt,all_triangles=True); hits=[]
    for i,j in a.overlap(b):
        x=[ap[k] for k in at[i]]; y=[bp[k] for k in bt[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(x,y),(y,x)] for k in range(3)): hits.append([i,j])
    return {'transverse_pairs':len(hits),'pairs':hits}
def neutral():
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    key.value=0; bpy.context.view_layer.update()
def saveblend(name):
    neutral(); p=OUT/name; bpy.ops.wm.save_as_mainfile(filepath=str(p)); return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
contact_before=event('wrist_loft_checkpoint'); before={ob.name:intersections(ob,bracer) for ob in [glove,tube]}; checkpoint=saveblend('ro_wrist_loft_checkpoint.blend')
save('loft-checkpoint.json',{'artifact':checkpoint,'surface_gate_pass':contact_before['surface_gate_pass'],'armor_before_trim':before})

# Collision positions from actual source put the interfering distal bracer at -29..-12mm.
# Trim to -52mm, retaining proximal outer detail. No planar cap is added over the cavity.
bm=bmesh.new(); bm.from_mesh(bracer.data); before_faces=len(bm.faces)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=wrist-axis*.052,plane_no=axis,clear_outer=True,clear_inner=False)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(bracer.data); bm.free(); bracer.data.update()
save('bracer-trim.json',{'cut_plane_axial_from_wrist_m':-.052,'measured_colliding_vertices_axial_range_m':[-.028681276366114616,-.01157624227926135],
 'faces_before':before_faces,'faces_after':len(bracer.data.polygons),'new_cap':False,'solid_inside_test_used_for_open_bracer':False,
 'preserved':'proximal source surface loops/materialUV copied by BMesh; source BLEND unchanged'})
contact_final=event('bracer_trim_checkpoint'); basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}; samples=[]
def render(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
for alpha in [0,.25,.5,.75,1]:
    guard()
    for pb in rig.pose.bones:
        m=basis[pb.name]; q=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha); b=q.to_matrix().to_4x4(); b.translation=m.translation*alpha; pb.matrix_basis=b
    bpy.context.view_layer.update(); update_wrist_helper(rig); key.value=alpha; bpy.context.view_layer.update()
    gp_eval,_,_=evaluated(glove); cp_eval,_,_=evaluated(core); tp,_,_=evaluated(tube)
    seam_core=max((tp[ranges[0][i]]-cp_eval[ci[i]]).length for i in range(len(ci))); seam_glove=max((tp[ranges[-1][i]]-gp_eval[gi[i]]).length for i in range(len(gi)))
    ratios=[((tp[e.vertices[0]]-tp[e.vertices[1]]).length/length,ident) for (ident,length),e in zip(rest_edges,tm.edges) if length>1e-8]
    collisions={ob.name:intersections(ob,bracer) for ob in [glove,tube,core]}
    samples.append({'alpha':alpha,'seam_core_max_gap_m':seam_core,'seam_glove_max_gap_m':seam_glove,'tube_edge_ratio_min_max':[min(ratios),max(ratios)],'bracer_collisions':collisions})
    render(QA/f'transition-{alpha:g}')
save('wrist-transition.json',samples); neutral(); render_views(QA/'whole-open'); artifact=saveblend('ro_wrist_loft.blend')
whole=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.data.calc_loop_triangles(); whole+=len(ob.data.loop_triangles)
report={'trial':'v006','finished_utc':datetime.now(timezone.utc).isoformat(),'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
 'surface_gate_pass':contact_final['surface_gate_pass'],'pad_contacts':contact_final['pad_contacts'],'maximum_penetration_m':contact_final['maximum_penetration_m'],'sword_crossings':contact_final['transverse_crossings_count'],
 'transition_samples':5,'seams_max_m':max(max(s['seam_core_max_gap_m'],s['seam_glove_max_gap_m']) for s in samples),
 'armor_crossing_pairs_by_sample':[{n:r['transverse_pairs'] for n,r in s['bracer_collisions'].items()} for s in samples],
 'whole_triangles':whole,'whole_budget_pass':whole<=60000,'art_acceptance':'pending actual fixed views','full_animation_accepted':False,'delivered':False,'artifact':artifact}
save('wrist-loft.json',report); print('RO_WRIST_LOFT '+json.dumps(report))
