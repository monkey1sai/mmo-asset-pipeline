"""v004: bounded contact corrective and continuous cuff weights, all poses replayed."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import sys
import bpy
import bmesh
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign,curl_digits
from ro_glove_contact_ik import configure
from ro_hand_gate import contacts,evaluated,sword_solid,inside
from ro_review_common import camera,render_views
BASEQA=ROOT/'runs/qa/ro-swordsman-combo-r006'; QA=BASEQA/'v004-corrective'; OUT=ROOT/'assets/processed/ro-swordsman-combo-r006/v004-corrective'
start=json.loads((BASEQA/'v004-start.json').read_text()); source=ROOT/start['source']['path']; clock=json.loads((BASEQA/'phase-start.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not QA.exists() and not OUT.exists()
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
guard(); bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; sword=bpy.data.objects['SM_RO_sword']; core=bpy.data.objects['SM_RO_core']
state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters']); pads=json.loads(glove['fixed_pad_indices'])
anatomy=json.loads((BASEQA/'v001-generated-glove/anatomy-and-masks.json').read_text())
rotation=Matrix(anatomy['rotation']); wrist=Vector(state['rest']['hand.R'][0]); source_wrist=Vector(anatomy['source_wrist'])
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
uv_before=[tuple(v.uv) for v in glove.data.uv_layers.active.data]
rest_before=[v.co.copy() for v in glove.data.vertices]
cuff_changed=[]
for v in glove.data.vertices:
    p=rotation.inverted()@(v.co-wrist)+source_wrist
    if p.z<.050:
        arm=max(0,min(1,(.050-p.z)/.032))
        assign(glove,v,{'lower_arm.R':arm,'hand.R':1-arm}); cuff_changed.append(v.index)
OUT.mkdir(parents=True); QA.mkdir(parents=True)
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
fixture=configure(rig,state,params)
# Skin inverse is exact for this LBS armature, no preserve-volume modifier.
matrices=[]
for v in glove.data.vertices:
    blend=Matrix(((0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)))
    for group in v.groups:
        n=glove.vertex_groups[group.group].name
        blend += (rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted())*group.weight
    matrices.append(blend)
basis=glove.shape_key_add(name='Basis')
corrective=glove.shape_key_add(name='GripContact_R')
corrective.value=1
events=[]
def measure(kind,iteration):
    guard(); r=contacts(glove,sword,rig,pads,'single-grip',{'joint_ik':params,'corrective_value':corrective.value,'iteration':iteration})
    r.update(event_kind=kind,event_number=len(events)+1,timestamp_utc=datetime.now(timezone.utc).isoformat(),fixture=fixture)
    events.append(r); save(QA/'corrective-events.json',events); return r
current=measure('initial_readback',0)
movement=[]
for iteration in range(1,start['maximum_corrective_iterations']+1):
    if current['surface_gate_pass']: break
    points,triangles,edges=evaluated(glove); sp,st,solid=sword_solid(sword)
    corrections={}
    for i,p in enumerate(points):
        nearest,normal,face,dist=solid.find_nearest(p)
        vote=inside(solid,p) if dist>1e-7 else False
        if vote is None: raise RuntimeError('Cannot sculpt against unknown solid parity')
        if vote:
            corrections[i]=nearest+normal*.0008
    # Move all vertices of crossing faces to the exterior of the actual crossed
    # sword face plane; this removes facet/edge crossings missed by vertices.
    for crossing in current['crossings']:
        t=triangles[crossing['glove_triangle']]
        centroid=sum((points[i] for i in t),Vector())/3
        nearest,normal,face,dist=solid.find_nearest(centroid)
        if normal is None: raise RuntimeError('Missing actual sword normal')
        for i in t:
            p=corrections.get(i,points[i])
            signed=(p-nearest).dot(normal)
            if signed<.0008:
                corrections[i]=p+normal*(.0008-signed)
    if not corrections: break
    rows=[]
    for i,target in corrections.items():
        restored=matrices[i].inverted()@target
        distance=(restored-rest_before[i]).length
        if distance>start['maximum_rest_corrective_m']:
            raise RuntimeError('Corrective exceeds5mm source-detail bound; preserve last valid stage')
        corrective.data[i].co=restored
        rows.append({'vertex':i,'rest_delta_m':distance,'posed_delta_m':(target-points[i]).length})
    bpy.context.view_layer.update()
    movement.append({'iteration':iteration,'changed_vertices':rows})
    save(QA/'corrective-movement.json',movement)
    current=measure('corrective_candidate',iteration)
final=measure('final_readback',len(movement))

# Proper wrist overlap sleeve. Actual core boundary is sampled; no center fan.
bm=bmesh.new(); bm.from_mesh(core.data)
edges=[e for e in bm.edges if e.is_boundary and all(v.co.x<-.34 and abs(v.co.z-.970)<1e-5 for v in e.verts)]
vertices=list({v for e in edges for v in e.verts}); center=sum((v.co for v in vertices),Vector())/len(vertices)
import math
vertices.sort(key=lambda v:math.atan2(v.co.y-center.y,v.co.x-center.x))
ring=[v.co.copy() for v in vertices]; bm.free()
if len(ring)<10: raise RuntimeError('Missing actual wrist attachment ring')
coords=[]; rows=3
hand_axis=(Vector(state['rest']['hand.R'][1])-wrist).normalized()
for k in range(rows):
    for p in ring: coords.append(p+hand_axis*(k*.015))
faces=[]; count=len(ring)
for k in range(rows-1):
    for j in range(count): faces.append((k*count+j,k*count+(j+1)%count,(k+1)*count+(j+1)%count,(k+1)*count+j))
mesh=bpy.data.meshes.new('RO_WristSleeve_R'); mesh.from_pydata(coords,[],faces); mesh.update()
sleeve=bpy.data.objects.new('SM_RO_WristSleeve.R',mesh); bpy.data.collections['COL_Character'].objects.link(sleeve)
from ro_review_common import material
mesh.materials.append(material('RO_Wrist_Leather',(.14,.063,.026),rough=.72))
uv=mesh.uv_layers.new(name='SleeveIsland')
for f in mesh.polygons:
    for li,vi in zip(f.loop_indices,f.vertices):
        uv.data[li].uv=(vi%count/count,vi//count/(rows-1))
    f.use_smooth=True
for v in mesh.vertices:
    k=v.index//count; amount=[0,.35,.70][k]
    assign(sleeve,v,{'lower_arm.R':1-amount,'hand.R':amount})
sleeve.parent=rig; sleeve.matrix_parent_inverse=Matrix.Identity(4)
mod=sleeve.modifiers.new('Skin','ARMATURE'); mod.object=rig

def views(folder):
    folder.mkdir(parents=True,exist_ok=False); target=rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
views(QA/'grip-R')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
corrective.value=0; bpy.context.view_layer.update(); render_views(QA/'whole-open'); views(QA/'open-R')
curl_digits(rig,state,'R',.30); views(QA/'small-curl-R')
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
corrective.value=0; bpy.context.view_layer.update()
assert uv_before==[tuple(v.uv) for v in glove.data.uv_layers.active.data]
assert all((a-v.co).length==0 for a,v in zip(rest_before,glove.data.vertices))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_glove_corrective.blend'))
whole=0
for ob in bpy.data.collections['COL_Character'].objects:
    if ob.type=='MESH': ob.data.calc_loop_triangles(); whole+=len(ob.data.loop_triangles)
report={'trial':'v004','finished_utc':datetime.now(timezone.utc).isoformat(),
    'shape_key':'GripContact_R','corrective_iterations':len(movement),'events':len(events),
    'maximum_rest_corrective_m':max((r['rest_delta_m'] for row in movement for r in row['changed_vertices']),default=0),
    'cuff_weight_vertices':len(cuff_changed),'new_sleeve_triangles':len(sleeve.data.loop_triangles),
    'source_geometry_and_uv_preserved':True,'whole_triangles':whole,
    'surface_gate_pass':final['surface_gate_pass'],'maximum_penetration_m':final['maximum_penetration_m'],
    'crossings':final['transverse_crossings_count'],'pad_contacts':final['pad_contacts'],
    'art_and_cuff_clearance':'pending actual visual/rigid-armor surface review',
    'whole_budget_pass':whole<=60000,'full_animation_accepted':False,'delivered':False,
    'source_preserved':hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256'],
    'artifact':{'path':(OUT/'ro_glove_corrective.blend').relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256((OUT/'ro_glove_corrective.blend').read_bytes()).hexdigest()}}
save(QA/'corrective.json',report); print('RO_GLOVE_CORRECTIVE '+json.dumps(report))
