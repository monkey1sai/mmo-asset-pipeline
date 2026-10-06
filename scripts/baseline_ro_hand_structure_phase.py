"""Actual r007 baseline of the preserved failed v008, with evaluated topology IDs."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_hand_gate import contacts,evaluated,segment_hit
from ro_review_common import camera,render_views
ID='ro-swordsman-combo-r007'
QA=ROOT/'runs/qa'/ID/'baseline'
OUT=ROOT/'assets/processed'/ID/'baseline'
clock=json.loads((QA.parent/'phase-start.json').read_text(encoding='utf-8'))
assert not QA.exists() and not OUT.exists(), 'Preserve baseline'
source=ROOT/clock['baseline_source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==clock['baseline_source']['sha256']
assert (datetime.now(timezone.utc)-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['trial_seconds']
QA.mkdir(parents=True); OUT.mkdir(parents=True)
files=[]
for suffix in ['.blend','.glb']:
    before=source.with_suffix(suffix)
    after=OUT/('ro_hand_structure_baseline'+suffix)
    shutil.copyfile(before,after)
    assert hashlib.sha256(before.read_bytes()).digest()==hashlib.sha256(after.read_bytes()).digest()
    files.append({'path':after.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(after.read_bytes()).hexdigest()})
for name in ['ro_hand_gate.py','ro_review_common.py']:
    shutil.copyfile(ROOT/'scripts'/name,QA/name)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'ro_hand_structure_baseline.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; glove=bpy.data.objects['SM_RO_glove.R']; tube=bpy.data.objects['SM_RO_WristLoft.R']; sword=bpy.data.objects['SM_RO_sword']
pads=json.loads(glove['fixed_pad_indices'])
subject_meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith('SM_RO_')]
canonical={}
for ob in [glove,tube]:
    assert 'r007_original_point_id' not in ob.data.attributes
    tag=ob.data.attributes.new('r007_original_point_id','INT','POINT')
    known={}; ids=[]
    for vertex,item in zip(ob.data.vertices,tag.data):
        item.value=vertex.index
        # Stable REST duplicate identity, never posed-distance welding.
        k=tuple(round(float(x),6) for x in vertex.co)
        ids.append(known.setdefault(k,vertex.index))
    canonical[ob.name]=ids


def self_diagnostic(ob):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh(); mesh.calc_loop_triangles()
    original=[r.value for r in mesh.attributes['r007_original_point_id'].data]
    assert original==list(range(len(ob.data.vertices))), 'Stable point identity is required'
    points=[ev.matrix_world@v.co for v in mesh.vertices]
    triangles=[tuple(t.vertices) for t in mesh.loop_triangles]
    polygons=[t.polygon_index for t in mesh.loop_triangles]
    ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
    hits=[]; adjacent_skipped=0; degenerate=sum((points[b]-points[a]).cross(points[c]-points[a]).length<1e-12 for a,b,c in triangles)
    for i,j in tree.overlap(tree):
        if i>=j: continue
        if {canonical[ob.name][k] for k in triangles[i]} & {canonical[ob.name][k] for k in triangles[j]}:
            adjacent_skipped+=1; continue
        left=[points[k] for k in triangles[i]]; right=[points[k] for k in triangles[j]]
        locations=[]
        for a,b in [(left,right),(right,left)]:
            for k in range(3):
                hit=segment_hit(a[k],a[(k+1)%3],b)
                if hit is not None: locations.append(list(hit))
        if locations: hits.append({'evaluated_triangle_pair':[i,j],'polygon_pair':[polygons[i],polygons[j]],'source_vertex_ids':[list(triangles[i]),list(triangles[j])],'locations':locations})
    return {'transverse_triangle_pairs':len(hits),'representative_crossings':hits[:20],
            'actual_evaluated_triangles_used':True,'vertex_order_verified_by_original_point_attribute':True,
            'rest_canonical_duplicate_vertices':len(canonical[ob.name])-len(set(canonical[ob.name])),
            'shared_rest_vertex_pairs_skipped':adjacent_skipped,'degenerate_triangles':degenerate,
            'limitations':['Transverse segment/triangle tests exclude coplanar/tangential contact','Stable coincident rest vertices may also merge touching disconnected surfaces; explicit raw IDs retained','Adjacent-face folds require additional visual inspection;zero is not complete art/self-intersectionPASS'],
            'pose_vertices_triangles_sha256':hashlib.sha256(json.dumps({'points':[list(p) for p in points],'triangles':triangles},sort_keys=True).encode()).hexdigest()}


def local_views(folder):
    folder.mkdir()
    target=rig.matrix_world@rig.pose.bones['hand.R'].head.lerp(rig.pose.bones['hand.R'].tail,.6)
    for name,offset in [('palm',(.25,-1,.12)),('side',(1,.1,.1)),('back',(-.25,1,.1)),('wrist',(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29))
        bpy.context.scene.render.filepath=str(folder/(name+'.png'))
        bpy.ops.render.render(write_still=True)


render_views(QA,frame=1)
samples=[]
for frame in [1,16,31,46,61]:
    bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    contact=contacts(glove,sword,rig,pads,'r007-baseline-readback',{'actual_baked_frame':frame,'source':'r006-v008','no_search':True})
    samples.append({'frame':frame,'contact':contact,'glove_self':self_diagnostic(glove),'wrist_self':self_diagnostic(tube)})
    local_views(QA/f'frame-{frame:03}')
bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
invalid=[]; maximum=0
for ob in subject_meshes:
    for vertex in ob.data.vertices:
        weights=[g for g in vertex.groups if g.weight>1e-8]
        maximum=max(maximum,len(weights))
        if not weights or len(weights)>4 or abs(sum(g.weight for g in weights)-1)>1e-5 or any(ob.vertex_groups[g.group].name not in rig.data.bones for g in weights):
            invalid.append({'mesh':ob.name,'vertex':vertex.index})
core_points,_,_=evaluated(bpy.data.objects['SM_RO_core'])
height=max(p.z for p in core_points)-min(p.z for p in core_points)
triangles=sum(len(evaluated(ob)[1]) for ob in subject_meshes)
images=[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE']
glb=OUT/'ro_hand_structure_baseline.glb'
import struct
data=glb.read_bytes(); assert data[:4]==b'glTF'; length,kind=struct.unpack_from('<II',data,12); assert kind==0x4E4F534A
doc=json.loads(data[20:20+length])
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'tool':bpy.app.version_string,
    'source':clock['baseline_source'],'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==clock['baseline_source']['sha256'],
    'artifact_copies_byte_identical_to_source':True,'artifacts':files,
    'full_views_frame':1,'local_samples':samples,'samples_are_baseline_readbacks_not_searches':True,
    'selfcross_method_changed_not_asset_improvement':True,
    'whole_character_triangles':triangles,'bones':len(rig.data.bones),'invalid_weights':invalid,'maximum_influences':maximum,
    'actual_core_height_m':height,'actual_core_floor_m':min(p.z for p in core_points),
    'source_GL B_inventory'.replace(' ',''):{'skins':len(doc.get('skins',[])),'animations':len(doc.get('animations',[])),'channels':sum(len(a['channels']) for a in doc.get('animations',[])),'images':len(doc.get('images',[]))},
    'source_clip_frames':[1,61],'full300frame_skills_present':False,'independent_required_effects_present':False,
    'images':images,'actual_fresh_glb_playback_this_baseline':'not_run; r00661frame verified report preserved separately',
    'art_verdict':'NO_SHIP','no_geometry_uv_weights_saved_or_changed':True,
    'temporary_point_identity_attribute':'Added in memory only; copied baseline BLEND/GLB stay byte-identical',
    'preview_artifacts':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(QA.rglob('*.png'))],
}
with (QA/'baseline.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,ensure_ascii=False,indent=2); stream.write('\n')
print(json.dumps({'baseline':'actual','triangles':triangles,'bones':len(rig.data.bones),'invalid_weights':len(invalid),
    'height_m':height,'glove_transverse_pairs':[s['glove_self']['transverse_triangle_pairs'] for s in samples],
    'wrist_transverse_pairs':[s['wrist_self']['transverse_triangle_pairs'] for s in samples],
    'PNGs':len(result['preview_artifacts']),'art':'NO_SHIP'}))
