"""v007 measured local underlay/cavity fit, cuff material and dependent gear budget."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,sys
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_hand_gate import contacts,evaluated,segment_hit
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v007-underlay'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v007-underlay'
start=json.loads((BASEQA/'v007-start.json').read_text()); clock=json.loads((BASEQA/'phase-start.json').read_text()); source=ROOT/start['source']['path']
assert not QA.exists() and not OUT.exists(); assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
def save(name,value): (QA/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False); QA.mkdir(parents=True); OUT.mkdir(parents=True)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; glove=bpy.data.objects['SM_RO_glove.R']; tube=bpy.data.objects['SM_RO_WristLoft.R']; bracer=bpy.data.objects['SM_RO_bracer.R']; sword=bpy.data.objects['SM_RO_sword']
state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); pads=json.loads(glove['fixed_pad_indices']); key=glove.data.shape_keys.key_blocks['GripContact_R']
ringdata=json.loads((BASEQA/'v006-wrist-loft-attempt2/ring-loft.json').read_text()); ci=ringdata['core_boundary_indices']; gi=ringdata['glove_boundary_indices']; ii=ringdata['inner_glove_boundary_indices']
sizes=[len(ci),48,48,48,len(gi),len(ci),48,48,48,len(ii)]; ranges=[]; acc=0
for size in sizes: ranges.append(list(range(acc,acc+size))); acc+=size
assert acc==len(tube.data.vertices)
wrist=Vector(state['rest']['hand.R'][0]); axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized()
bp,bt,_=evaluated(bracer); bvh=BVHTree.FromPolygons(bp,bt,all_triangles=True)
original_core=[v.co.copy() for v in core.data.vertices]; original_uv=[list(l.uv) for l in core.data.uv_layers.active.data]; covered=[]; directions={}; coverage=[]
for vert in core.data.vertices:
    d=vert.co-wrist; t=d.dot(axis); radial=d-axis*t; w={core.vertex_groups[g.group].name:g.weight for g in vert.groups}
    if not(-.265<t<0 and radial.length<.095 and w.get('lower_arm.R',0)>.8): continue
    direction=radial.normalized(); center=wrist+axis*t; origin=center.copy(); traveled=0; hits=[]
    for _ in range(12):
        p,n,face,distance=bvh.ray_cast(origin,direction,.18-traveled)
        if p is None: break
        traveled+=distance; hits.append(traveled); origin=p+direction*1e-6; traveled+=1e-6
    if hits or vert.index in ci:
        covered.append(vert.index); directions[vert.index]=(t,radial.length,direction); coverage.append({'id':vert.index,'axial_m':t,'source_radius_m':radial.length,'radial_gear_envelope_m':max(hits) if hits else None,'matched_wrist_ring':vert.index in ci})
assert all(i in covered for i in ci),'Preserve actual wrist ring unless complete regional mapping exists'
save('frozen-regional-underlay-mask.json',{'vertex_ids':covered,'coverage':coverage,'before_change':True,
 'definition':'own lower_arm.R>0.8, axial(-.265,0), radius<95mm, actual radial gear hit or existing39vertex wrist ring; all other core points protected',
 'evidence':'covered-forearm-diagnosis.json all5shows62common intersection faces; brace is rigid tosame forearm branch, coverage ray rest frame held; radial coverage is diagnostic only',
 'proximal_falloff':'smoothstep from0at-.265m to1at-.215m; preserve exposed proximal sleeve boundary'})
changes=[]
for i in covered:
    t,radius,direction=directions[i]; a=max(0,min(1,(t+.265)/.05)); a=a*a*(3-2*a); target_radius=min(radius,.0275+.003*max(0,min(1,(-t-.06)/.15)))
    new_radius=radius+(target_radius-radius)*a; new=wrist+axis*t+direction*new_radius; core.data.vertices[i].co=new; changes.append({'id':i,'displacement_m':(new-original_core[i]).length})
core.data.update(); protected=[i for i in range(len(core.data.vertices)) if i not in set(covered)]
assert all((core.data.vertices[i].co-original_core[i]).length<1e-8 for i in protected)
assert original_uv==[list(l.uv) for l in core.data.uv_layers.active.data]
save('underlay-change.json',{'changed_region_vertices':len(covered),'protected_vertices_checked':len(protected),'protected_max_delta_m':0,'all_core_uv_readback_equal':True,
 'maximum_regional_displacement_m':max(r['displacement_m'] for r in changes),'changes':changes,'geometry_scope':'Substantial derived fitting of old integrated armor bulges; not called micro-detail repair'})

# Update actual two-layer tube endpoints, then resample the existing graph phase by arclength.
def resample(points,n):
    distances=[(b-a).length for a,b in zip(points,points[1:]+points[:1])]; total=sum(distances); q=[0]
    for d in distances: q.append(q[-1]+d/total)
    result=[]
    for i in range(n):
        t=i/n; j=next(j for j in range(len(points)) if q[j]<=t<=q[j+1]); result.append(points[j].lerp(points[(j+1)%len(points)],(t-q[j])/(q[j+1]-q[j])))
    return result
cp=[core.data.vertices[i].co.copy() for i in ci]; centroid=sum(cp,Vector())/len(cp)
ic=[p-(p-centroid-axis*(p-centroid).dot(axis)).normalized()*.0025 for p in cp]
gp=[glove.data.shape_keys.key_blocks['Basis'].data[i].co.copy() for i in gi]; ip=[glove.data.shape_keys.key_blocks['Basis'].data[i].co.copy() for i in ii]
for offset,a,b in [(0,cp,gp),(5,ic,ip)]:
    for index,co in zip(ranges[offset],a): tube.data.vertices[index].co=co
    for index,co in zip(ranges[offset+4],b): tube.data.vertices[index].co=co
    ar=resample(a,48); br=resample(b,48)
    for row,t in [(1,.25),(2,.5),(3,.75)]:
        for index,p,q in zip(ranges[offset+row],ar,br): tube.data.vertices[index].co=p.lerp(q,t)
tube.data.update()

# Actual source cap/strap surfaces can occupy the inside of the wearable gear.
# A closed local cylinder cutter clears a31mm cavity; open bracer is tested by actual triangles.
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.031,depth=.62,end_fill_type='NGON',location=tuple(wrist-axis*.15),rotation=Vector((0,0,1)).rotation_difference(axis).to_euler())
cutter=bpy.context.object; cutter.name='TMP_RO_BracerCavity'; before_bracer=len(bracer.data.polygons); mod=bracer.modifiers.new('MeasuredCavity','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
bpy.ops.object.select_all(action='DESELECT'); bracer.select_set(True); bpy.context.view_layer.objects.active=bracer; bpy.ops.object.modifier_apply(modifier=mod.name); bpy.data.objects.remove(cutter,do_unlink=True)
save('bracer-cavity.json',{'radius_m':.031,'axis':'actual lower_arm.R rest head-to-tail','faces_before':before_bracer,'faces_after':len(bracer.data.polygons),
 'method':'closed cylinder Boolean exact difference; new internal surfaces visible only in cavity; source exteriorUV retained by Boolean, needs visual review',
 'bracer_inside_classification':'not_used; cut bracer is open, actual transverse triangle test required'})

# Preserve finger density; two rigid shoulder pieces carry the dependent whole-character reduction.
reductions=[]
for side in ['R','L']:
    ob=bpy.data.objects['SM_RO_pauldron.'+side]; ob.data.calc_loop_triangles(); before=len(ob.data.loop_triangles)
    dec=ob.modifiers.new('DependentRigidBudget','DECIMATE'); dec.ratio=.72; dec.use_collapse_triangulate=True; dec.delimit={'UV','MATERIAL'}
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob; bpy.ops.object.modifier_apply(modifier=dec.name)
    ob.data.calc_loop_triangles(); reductions.append({'object':ob.name,'before_triangles':before,'after_triangles':len(ob.data.loop_triangles),'ratio_requested':.72,'delimit':['UV','MATERIAL'],'acceptance':'pending same five whole views'})
save('dependent-gear-budget.json',reductions)

# Explicit2K leather maps; deterministic procedural authoring, no borrowed/edited reference pixels.
mat=tube.data.materials[0]; nt=mat.node_tree; bs=nt.nodes.get('Principled BSDF'); size=2048
y,x=np.mgrid[0:size,0:size].astype(np.float32); x/=size; y/=size
grain=.5+.19*np.sin(2*np.pi*(x*127+y*61))+.15*np.sin(2*np.pi*(x*193-y*97))+.10*np.sin(2*np.pi*(x*29+y*23))
color=np.empty((size,size,4),np.float32)
for c,value in enumerate([.29,.19,.13]): color[:,:,c]=value*(.91+.18*grain)
color[:,:,3]=1
image=bpy.data.images.new('RO_WristLeather_BaseColor_2K',width=size,height=size,alpha=True); image.colorspace_settings.name='sRGB'; image.pixels.foreach_set(color.ravel()); image.update(); image.filepath_raw=str(OUT/'wrist_leather_basecolor.png'); image.file_format='PNG'; image.save(); image.pack()
tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=image; nt.links.new(tex.outputs['Color'],bs.inputs['Base Color']); bs.inputs['Roughness'].default_value=.72
dx=(np.roll(grain,-1,axis=1)-np.roll(grain,1,axis=1))*.065; dy=(np.roll(grain,-1,axis=0)-np.roll(grain,1,axis=0))*.065
normal=np.empty((size,size,4),np.float32); normal[:,:,0]=.5-dx; normal[:,:,1]=.5-dy; normal[:,:,2]=1; normal[:,:,3]=1
imn=bpy.data.images.new('RO_WristLeather_Normal_2K',width=size,height=size,alpha=True); imn.colorspace_settings.name='Non-Color'; imn.pixels.foreach_set(normal.ravel()); imn.update(); imn.filepath_raw=str(OUT/'wrist_leather_normal.png'); imn.file_format='PNG'; imn.save(); imn.pack()
tn=nt.nodes.new('ShaderNodeTexImage'); tn.image=imn; normalnode=nt.nodes.new('ShaderNodeNormalMap'); normalnode.inputs['Strength'].default_value=.55; nt.links.new(tn.outputs['Color'],normalnode.inputs['Color']); nt.links.new(normalnode.outputs['Normal'],bs.inputs['Normal'])
save('wrist-material.json',{'size':[2048,2048],'method':'deterministic authored periodic fine leather grain plus tangent normal','reference_pixels_used':False,
 'textures':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [OUT/'wrist_leather_basecolor.png',OUT/'wrist_leather_normal.png']],
 'packed_in_blend':True,'source_glove_material_unchanged':True,'art_acceptance':'pending assembled texture comparison'})

def intersections(aob,bob):
    ap,at,_=evaluated(aob); bp,bt,_=evaluated(bob); a=BVHTree.FromPolygons(ap,at,all_triangles=True); b=BVHTree.FromPolygons(bp,bt,all_triangles=True); hits=[]
    for i,j in a.overlap(b):
        left=[ap[k] for k in at[i]]; right=[bp[k] for k in bt[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(left,right),(right,left)] for k in range(3)): hits.append([i,j])
    return {'transverse_pairs':len(hits),'pairs':hits}
key.value=1; configure(rig,state,params); contact=contacts(glove,sword,rig,pads,'single-grip',{'checkpoint':'regional_underlay_cavity','joint_ik':params})
contact.update(event_kind='final_readback',event_number=1,timestamp_utc=datetime.now(timezone.utc).isoformat()); save('contact-events.json',[contact]); pose_basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}
rest_lengths=[(tube.data.vertices[e.vertices[0]].co-tube.data.vertices[e.vertices[1]].co).length for e in tube.data.edges]; samples=[]
def render(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
for alpha in [0,.25,.5,.75,1]:
    guard()
    for pb in rig.pose.bones:
        m=pose_basis[pb.name]; b=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha).to_matrix().to_4x4(); b.translation=m.translation*alpha; pb.matrix_basis=b
    bpy.context.view_layer.update(); update_wrist_helper(rig); key.value=alpha; bpy.context.view_layer.update()
    gp,_,_=evaluated(glove); cp,_,_=evaluated(core); tp,_,_=evaluated(tube)
    seams=max(max((tp[ranges[0][i]]-cp[ci[i]]).length for i in range(len(ci))),max((tp[ranges[4][i]]-gp[gi[i]]).length for i in range(len(gi))),max((tp[ranges[9][i]]-gp[ii[i]]).length for i in range(len(ii))))
    ratios=[((tp[e.vertices[0]]-tp[e.vertices[1]]).length/rest,index) for index,(e,rest) in enumerate(zip(tube.data.edges,rest_lengths)) if rest>1e-8]
    samples.append({'alpha':alpha,'seams_max_m':seams,'tube_edge_ratio_min_max':[min(ratios),max(ratios)],'armor_collisions':{ob.name:intersections(ob,bracer) for ob in [glove,tube,core]}})
    render(QA/f'transition-{alpha:g}')
save('wrist-transition.json',samples)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
key.value=0; bpy.context.view_layer.update(); render_views(QA/'whole-open'); p=OUT/'ro_underlay_fit.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(p))
whole=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.data.calc_loop_triangles(); whole+=len(ob.data.loop_triangles)
report={'trial':'v007','finished_utc':datetime.now(timezone.utc).isoformat(),'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
 'surface_gate_pass':contact['surface_gate_pass'],'pad_contacts':contact['pad_contacts'],'maximum_penetration_m':contact['maximum_penetration_m'],'sword_crossings':contact['transverse_crossings_count'],
 'whole_triangles':whole,'whole_budget_pass':whole<=60000,'seams_max_m':max(s['seams_max_m'] for s in samples),
 'armor_crossings_by_sample':[{n:r['transverse_pairs'] for n,r in s['armor_collisions'].items()} for s in samples],
 'maximum_underlay_delta_m':max(r['displacement_m'] for r in changes),'art_acceptance':'pending actual fixed views','full_animation_accepted':False,'delivered':False,
 'artifact':{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}
save('underlay-fit.json',report); print('RO_UNDERLAY_FIT '+json.dumps(report))
