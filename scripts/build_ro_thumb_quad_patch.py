"""Build a local ring-and-grid thumb cap, preserving the actual native boundary."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_hand_gate import segment_hit
from ro_review_common import camera,material
BASE=ROOT/'runs/qa/ro-swordsman-combo-r007';QA=BASE/'v003-thumb-patch';OUT=ROOT/'assets/processed/ro-swordsman-combo-r007/v003-thumb-patch'
start=json.loads((BASE/'v003-start.json').read_text());clock=json.loads((BASE/'phase-start.json').read_text())
boundary=json.loads((QA/'boundary.json').read_text())['selected'];assert boundary
probe=json.loads((ROOT/start['joint_probe']['path']).read_text());source=ROOT/start['source']['path']
assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
assert not OUT.exists();OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];me=ob.data;me.calc_loop_triangles()
old_points=[v.co.copy() for v in me.vertices];old_ts=[tuple(t.vertices) for t in me.loop_triangles]
old_loops=[tuple(t.loops) for t in me.loop_triangles];old_uv=[u.uv.copy() for u in me.uv_layers.active.data]
reference=BVHTree.FromPolygons(old_points,old_ts,all_triangles=True)
removed=set(boundary['removed_faces']);ring_ids=boundary['loop_vertices'];assert len(ring_ids)==16
protected=[(tuple(f.vertices),[tuple(old_uv[i]) for i in f.loop_indices]) for f in me.polygons if f.index not in removed]
old_surface_samples=[]
for t in me.loop_triangles:
    if t.polygon_index not in removed:continue
    a,b,c=[old_points[i] for i in t.vertices]
    old_surface_samples += [a,b,c,(a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2]
bands=[(Vector(x['center']),Vector(x['axis']),x['half_axial_m'],x['radius_m']) for x in probe['thumb_flex_band_parameters']]
ip,axis,half,radius=bands[2]
directions=[]
for i in ring_ids:
    delta=old_points[i]-ip;directions.append((delta-axis*delta.dot(axis)).normalized())
events=[];best=None
def guard():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
def ray_section(height,direction):
    origin=ip+axis*height
    hit=reference.ray_cast(origin,direction,.04)
    assert hit[0] is not None
    return hit[0]
def uv_at(point):
    hit=reference.find_nearest(point);a,b,c=old_ts[hit[2]]
    la,lb,lc=old_loops[hit[2]]
    value=barycentric_transform(hit[0],old_points[a],old_points[b],old_points[c],
        Vector((*old_uv[la],0)),Vector((*old_uv[lb],0)),Vector((*old_uv[lc],0)))
    return (value.x,value.y),hit[2]
def build(heights):
    points=[p.copy() for p in old_points];faces=[tuple(f.vertices) for f in me.polygons if f.index not in removed]
    keep_count=len(faces);previous=ring_ids.copy();rings=[]
    for height in heights:
        ring=[]
        for d in directions:ring.append(len(points));points.append(ray_section(height,d))
        for i in range(16):faces.append((previous[i],previous[(i+1)%16],ring[(i+1)%16],ring[i]))
        rings.append(ring);previous=ring
    # Four-by-four quad grid, with four valence-three corners on the distal cap.
    grid={};last=[points[i] for i in previous]
    for i in range(5):
        grid[(i,0)]=previous[i];grid[(4,i)]=previous[4+i]
        grid[(i,4)]=previous[12-i];grid[(0,i)]=previous[(16-i)%16]
    for y in range(1,4):
        v=y/4
        for x in range(1,4):
            u=x/4
            p=(last[x]*(1-v)+last[12-x]*v+last[(16-y)%16]*(1-u)+last[4+y]*u
                -last[0]*(1-u)*(1-v)-last[4]*u*(1-v)-last[8]*u*v-last[12]*(1-u)*v)
            radial=p-ip-axis*(p-ip).dot(axis)
            hit=reference.ray_cast(ip+radial+axis*.05,-axis,.06)
            assert hit[0] is not None
            grid[(x,y)]=len(points);points.append(hit[0])
    for y in range(4):
        for x in range(4):faces.append((grid[x,y],grid[x+1,y],grid[x+1,y+1],grid[x,y+1]))
    # Strip/grid orientation is repaired locally against the original source normals.
    for index in range(keep_count,len(faces)):
        f=faces[index];p=sum((points[i] for i in f),Vector())/4
        n=(points[f[1]]-points[f[0]]).cross(points[f[2]]-points[f[0]])
        if n.dot(reference.find_nearest(p)[1])<0:faces[index]=tuple(reversed(f))
    used=sorted(set(i for f in faces for i in f));mapping={old:new for new,old in enumerate(used)}
    mesh=bpy.data.meshes.new('ThumbPatchCandidate');mesh.from_pydata([points[i] for i in used],[],[[mapping[i] for i in f] for f in faces]);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap');transfer=[]
    for f in mesh.polygons:
        if f.index<keep_count:
            oldface,values=protected[f.index]
            assert tuple(used[i] for i in f.vertices)==oldface
            for li,value in zip(f.loop_indices,values):uv.data[li].uv=value
        else:
            tri_ids=[]
            for li in f.loop_indices:
                value,tri=uv_at(mesh.vertices[mesh.loops[li].vertex_index].co);uv.data[li].uv=value;tri_ids.append(tri)
            transfer.append({'face':f.index,'nearest_original_triangle_per_corner':tri_ids})
    ids=mesh.attributes.new('r007_original_point_id','INT','POINT')
    source_ids=mesh.attributes.new('r007_source_point_id','INT','POINT')
    for i,old in enumerate(used):ids.data[i].value=i;source_ids.data[i].value=old+1 if old<len(old_points) else 0
    for m in me.materials:mesh.materials.append(m)
    for f in mesh.polygons:f.use_smooth=True
    return mesh,used,keep_count,transfer
def check(mesh,used,keep_count):
    mesh.calc_loop_triangles();pts=[v.co.copy() for v in mesh.vertices];ts=[tuple(t.vertices) for t in mesh.loop_triangles]
    tree=BVHTree.FromPolygons(pts,ts,all_triangles=True)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update()
    primary=[];new_poles=[];wrong=[]
    for v in bm.verts:
        if len(v.link_edges)==4:continue
        memberships=[i for i,(c,d,a,r) in enumerate(bands) if abs((v.co-c).dot(d))<=a and ((v.co-c)-d*(v.co-c).dot(d)).length<=r]
        if memberships:primary.append({'vertex':v.index,'valence':len(v.link_edges),'bands':memberships})
        if used[v.index]>=len(old_points):
            along=(v.co-ip).dot(axis);new_poles.append({'vertex':v.index,'valence':len(v.link_edges),'IP_axial_m':along})
            if along<half+start['cap_margin_m']:wrong.append(v.index)
    boundaries=[e for e in bm.edges if e.is_boundary]
    manifold=all(e.is_manifold or e.is_boundary for e in bm.edges)
    boundary2=all(sum(e.is_boundary for e in v.link_edges)==2 for e in boundaries for v in e.verts)
    bm.free();new_samples=[];degenerate=0;normal_wrong=0
    for t in mesh.loop_triangles:
        a,b,c=[pts[i] for i in t.vertices]
        if (b-a).cross(c-a).length<1e-12:degenerate+=1
        if t.polygon_index>=keep_count:
            new_samples += [a,b,c,(a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2]
            if (b-a).cross(c-a).dot(reference.find_nearest((a+b+c)/3)[1])<=0:normal_wrong+=1
    distances=[reference.find_nearest(p)[3] for p in new_samples]+[tree.find_nearest(p)[3] for p in old_surface_samples]
    crossings=[]
    for i,j in tree.overlap(tree):
        if i>=j or set(ts[i])&set(ts[j]):continue
        a=[pts[k] for k in ts[i]];b=[pts[k] for k in ts[j]]
        if any(segment_hit(l[k],l[(k+1)%3],r) is not None for l,r in [(a,b),(b,a)] for k in range(3)):crossings.append([i,j])
    uv_pass=all(all((mesh.uv_layers.active.data[li].uv-Vector(old)).length<1e-7 for li,old in zip(f.loop_indices,protected[f.index][1])) for f in mesh.polygons[:keep_count])
    protected_position_pass=all((pts[i]-old_points[old]).length<1e-9 for i,old in enumerate(used) if old<len(old_points))
    gate=not primary and not wrong and not degenerate and not normal_wrong and not crossings and manifold and boundary2 and len(boundaries)==18 and uv_pass and protected_position_pass and max(distances)<=start['surface_max_error_m']
    return {'primary_band_poles':primary,'new_cap_poles':new_poles,'pole_wrong_destination':wrong,
        'sampled_bidirectional_surface_max_m':max(distances),'surface_samples':len(distances),
        'neutral_transverse_pairs':len(crossings),'crossing_pairs':crossings[:20],
        'degenerate_triangles':degenerate,'new_triangle_wrong_normals':normal_wrong,
        'manifold_except_cuff':manifold,'boundary_degree2':boundary2,'boundary_edges':len(boundaries),
        'protected_positions_pass':protected_position_pass,'protected_corner_UV_pass':uv_pass,
        'protected_faces':keep_count,'triangles':len(ts),'quads':sum(len(f.vertices)==4 for f in mesh.polygons),'source_gate':gate}
variants=[[-.002,.004,.009,.0105],[-.003,0,.004,.007,.0105],[-.002,.002,.005,.008,.0105],[-.003,0,.003,.006,.009,.0105]]
for heights in variants:
    guard();mesh,used,keep_count,transfer=build(heights);result=check(mesh,used,keep_count)
    events.append({'heights_m':heights,'geometry':result})
    score=(int(not result['source_gate']),len(result['primary_band_poles'])+len(result['pole_wrong_destination']),result['new_triangle_wrong_normals']+result['neutral_transverse_pairs'],result['sampled_bidirectional_surface_max_m'])
    if best is None or score<best[0]:
        if best:bpy.data.meshes.remove(best[1])
        best=(score,mesh,used,keep_count,transfer,heights,result)
    else:bpy.data.meshes.remove(mesh)
    if result['source_gate']:break
ob.data=best[1];geometry=best[-1]
artifact=OUT/'right_hand_quad_patch.blend';bpy.ops.wm.save_as_mainfile(filepath=str(artifact))
# Textured views and gray wire views are separate diagnostic renders, never saved over the artifact.
views={'front':(0,-1,.16),'back':(0,1,.16),'three-quarter':(.6,-1,.36)}
for n,loc in views.items():
    camera((loc,(0,0,.155),.35));bpy.context.scene.render.filepath=str(QA/(n+'-texture.png'));bpy.ops.render.render(write_still=True)
gray=material('ThumbPatchGray',(.55,.55,.55));wire=material('ThumbPatchWire',(.005,.007,.009))
ob.data.materials.clear();ob.data.materials.append(gray);ob.data.materials.append(wire)
for f in ob.data.polygons:f.material_index=0
mod=ob.modifiers.new('DiagnosticWire','WIREFRAME');mod.thickness=.00028;mod.use_replace=False;mod.material_offset=1
for n,loc in views.items():
    camera((loc,(0,0,.155),.35));bpy.context.scene.render.filepath=str(QA/(n+'-wire.png'));bpy.ops.render.render(write_still=True)
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'boundary_record':{'path':(QA/'boundary.json').relative_to(ROOT).as_posix(),'sha256':hashlib.sha256((QA/'boundary.json').read_bytes()).hexdigest()},
    'method':'Preserved16vertex native loop; quad tubular rings and4x4grid cap on measured original surface',
    'removed_native_faces':len(removed),'actual_variants':len(events),'maximum_variants':start['maximum_patch_variants'],
    'selected_heights_m':best[-2],'geometry':geometry,'events':events,'UV_transfer':best[4],
    'joint_centers_and_bands_unchanged':True,'rig_created':False,'animation_topology_accepted':False,
    'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
    'limitations':['Bidirectional finite surface samples are not a continuous equivalence proof','Nearest source triangle per changed corner may cross UV seams; actual texture views required','No posed-skin acceptance yet']}
(QA/'patch.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RO_THUMB_PATCH '+json.dumps({'actual_variants':len(events),'geometry':geometry}))
