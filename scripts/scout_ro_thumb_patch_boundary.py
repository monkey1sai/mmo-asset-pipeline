"""Find a real closed native quad loop proximal to the thumb IP band."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'runs/qa/ro-swordsman-combo-r007'
start=json.loads((BASE/'v003-start.json').read_text());probe=json.loads((ROOT/start['joint_probe']['path']).read_text())
source=ROOT/start['source']['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==start['source']['sha256']
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];bm=bmesh.new();bm.from_mesh(ob.data)
bm.verts.ensure_lookup_table();bm.verts.index_update();bm.edges.index_update();bm.faces.index_update()
band=probe['thumb_flex_band_parameters'][2];center=Vector(band['center']);axis=Vector(band['axis'])
tip=Vector(probe['scaled_landmarks']['thumb'][-1])
tip_vertex=min(bm.verts,key=lambda v:(v.co-tip).length)
def along(v):return (v.co-center).dot(axis)
def radial(v):
    d=v.co-center;return (d-axis*d.dot(axis)).length
def walk(edge,start_vertex):
    edges=[edge];verts=[start_vertex];v=edge.other_vert(start_vertex)
    for _ in range(100):
        if v==start_vertex:return verts,edges
        if len(v.link_edges)!=4:return None
        verts.append(v);current=edges[-1]
        options=[e for e in v.link_edges if e!=current and not set(e.link_faces)&set(current.link_faces)]
        if len(options)!=1:return None
        new=options[0]
        if new in edges:return None
        edges.append(new);v=new.other_vert(v)
    return None
loops={}
for e in bm.edges:
    if all(-.026<along(v)<.001 and radial(v)<.025 for v in e.verts):
        result=walk(e,e.verts[0])
        if result:
            vs,es=result
            if all(-.030<along(v)<.003 and radial(v)<.026 for v in vs):
                loops[tuple(sorted(e.index for e in es))]=(vs,es)
events=[];accepted=[]
for vs,es in sorted(loops.values(),key=lambda x:abs(sum(along(v) for v in x[0])/len(x[0])+.013))[:start['maximum_boundary_probes']]:
    barrier=set(es);todo=[tip_vertex.link_faces[0]];part=set()
    while todo:
        f=todo.pop()
        if f in part:continue
        part.add(f)
        for e in f.edges:
            if e not in barrier:todo.extend(g for g in e.link_faces if g not in part)
    boundary=[e for e in bm.edges if sum(f in part for f in e.link_faces)==1 and any(f in part for f in e.link_faces)]
    retained_edges={e for e in bm.edges if any(f not in part for f in e.link_faces)}
    retained_degrees=[sum(e in retained_edges for e in v.link_edges) for v in vs]
    event={'loop_vertices':[v.index for v in vs],'loop_edges':[e.index for e in es],
        'mean_IP_axial_m':sum(along(v) for v in vs)/len(vs),'IP_axial_range_m':[min(along(v) for v in vs),max(along(v) for v in vs)],
        'removed_faces':[f.index for f in part],'removed_face_count':len(part),'retained_boundary_degrees':retained_degrees,
        'actual_boundary_matches_loop':set(boundary)==barrier,
        'only_distal_thumb':all(radial(v)<.030 and along(v)>-.033 for f in part for v in f.verts),
        'quad_bridge_eligible':len(vs)%2==0 and len(vs)>=8 and len(part)<100 and set(boundary)==barrier and all(n==3 for n in retained_degrees)}
    events.append(event)
    if event['quad_bridge_eligible']:accepted.append(event)
selected=next((e for e in accepted if e['only_distal_thumb']),None)
qa=BASE/'v003-thumb-patch';qa.mkdir()
value={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'actual_boundary_probes':len(events),
    'maximum_boundary_probes':start['maximum_boundary_probes'],'events':events,'selected':selected,
    'source_gate':False,'rig_created':False,'original_joint_masks_unchanged':True}
(qa/'boundary.json').write_text(json.dumps(value,indent=2)+'\n')
bm.free()
print('RO_PATCH_BOUNDARY '+json.dumps({'probes':len(events),'eligible':len(accepted),'selected':selected}))
