"""Read-only v006 core/gear diagnosis and protected cut data readback."""
from pathlib import Path
import json,sys,hashlib
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure
from ro_review_common import camera
QA=ROOT/'runs/qa/ro-swordsman-combo-r006/v006-underlay-diagnosis'; assert not QA.exists(); QA.mkdir()
newpath=ROOT/'assets/processed/ro-swordsman-combo-r006/v006-wrist-loft-attempt2/ro_wrist_loft.blend'
oldpath=ROOT/'assets/processed/ro-swordsman-combo-r006/v005-thumb-wrist/ro_thumb_contact_checkpoint.blend'
mapping=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r006/v006-wrist-loft-attempt2/semantic-cut-map.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(oldpath),load_ui=False,use_scripts=False); ob=bpy.data.objects['SM_RO_glove.R']; ob.data.calc_loop_triangles()
kept={int(i):j for i,j in mapping['original_to_new'].items()}; expected={}
for tri in ob.data.loop_triangles:
    if all(i in kept for i in tri.vertices):
        expected[tuple(kept[i] for i in tri.vertices)]=[list(ob.data.uv_layers.active.data[l].uv) for l in tri.loops]
oldprops={j:{'basis':list(ob.data.shape_keys.key_blocks['Basis'].data[i].co),'key':list(ob.data.shape_keys.key_blocks['GripContact_R'].data[i].co),
              'weights':{ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[i].groups}} for i,j in kept.items()}
bpy.ops.wm.open_mainfile(filepath=str(newpath),load_ui=False,use_scripts=False); rig=bpy.data.objects['ARM_RO_Swordsman']; state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters'])
glove=bpy.data.objects['SM_RO_glove.R']; glove.data.calc_loop_triangles(); actual={}
for tri in glove.data.loop_triangles:
    ids=tuple(tri.vertices)
    if ids in expected: actual[ids]=[list(glove.data.uv_layers.active.data[l].uv) for l in tri.loops]
uv_errors=[t for t in expected if t not in actual or any((Vector(a)-Vector(b)).length>1e-7 for a,b in zip(expected[t],actual[t]))]
geomerrors=[]; weighterrors=[]
for i,e in oldprops.items():
    if (glove.data.shape_keys.key_blocks['Basis'].data[i].co-Vector(e['basis'])).length>1e-8 or (glove.data.shape_keys.key_blocks['GripContact_R'].data[i].co-Vector(e['key'])).length>1e-8: geomerrors.append(i)
    w={glove.vertex_groups[g.group].name:g.weight for g in glove.data.vertices[i].groups}
    if set(w)!=set(e['weights']) or any(abs(w[n]-e['weights'][n])>1e-7 for n in w): weighterrors.append(i)
core=bpy.data.objects['SM_RO_core']; bracer=bpy.data.objects['SM_RO_bracer.R']; wrist=Vector(state['rest']['hand.R'][0]); axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized(); rows=[]
for ob in [core,bracer]:
    selected=[]
    for vert in ob.data.vertices:
        d=vert.co-wrist; t=d.dot(axis); radius=(d-axis*t).length; influences={ob.vertex_groups[g.group].name:g.weight for g in vert.groups}
        if -.225<t<-.025 and radius<.13 and influences.get('lower_arm.R',0)>.4:
            selected.append({'id':vert.index,'axial_m':t,'radius_m':radius,'weights':influences,'position':list(vert.co)})
    rows.append({'object':ob.name,'vertex_count':len(ob.data.vertices),'selected_forearm':selected,'modifiers':[(m.name,m.type) for m in ob.modifiers],
                 'axial_radial_bounds':[min(v['axial_m'] for v in selected),max(v['axial_m'] for v in selected),min(v['radius_m'] for v in selected),max(v['radius_m'] for v in selected)] if selected else None})
def views(folder,visible):
    folder.mkdir()
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH': ob.hide_render=ob.name not in visible
    target=rig.pose.bones['lower_arm.R'].head.lerp(rig.pose.bones['lower_arm.R'].tail,.7)
    for name,offset in [('front',(0,-1,.2)),('side',(1,0,.1)),('back',(0,1,.2))]:
        camera((tuple(target+Vector(offset)),tuple(target),.32)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
views(QA/'rest-core',['SM_RO_core']); views(QA/'rest-bracer',['SM_RO_bracer.R'])
configure(rig,state,params); glove.data.shape_keys.key_blocks['GripContact_R'].value=1; bpy.context.view_layer.update(); views(QA/'grip-core',['SM_RO_core']); views(QA/'grip-bracer',['SM_RO_bracer.R'])
result={'subject_sha256':hashlib.sha256(newpath.read_bytes()).hexdigest(),'old_source_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),
 'protected_vertices_tested':len(oldprops),'protected_triangles_uv_tested':len(expected),'uv_errors':uv_errors,'basis_or_contact_shape_errors':geomerrors,'weight_errors':weighterrors,
 'protected_readback_pass':not(uv_errors or geomerrors or weighterrors),'objects':rows,'diagnostic_only':True}
(QA/'underlay.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='objects'})); print(json.dumps([{'name':r['object'],'selection':len(r['selected_forearm']),'bounds':r['axial_radial_bounds']} for r in rows]))
