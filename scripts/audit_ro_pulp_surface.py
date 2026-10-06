"""Append fixed-pad normals, boundary gradients and actual wireframes; no repair."""
from pathlib import Path
from datetime import datetime,timezone
import sys,bpy
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
from ro_hand_gate import evaluated
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
name=sys.argv[-1];assert name in ['v002-pulp-corrective','v003-index-pulp']
folder=QA/name;result=read(folder/'result.json');contract=read(QA/'local-contract.json')
assert artifact(ROOT/result['artifact']['path'])==result['artifact']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
assert all(max(abs(ob.matrix_world[i][j]-Matrix.Identity(4)[i][j]) for i in range(4) for j in range(4))<1e-8 for ob in [ob,rig,sword])
points,tris,edges=evaluated(ob);sp,st,_=evaluated(sword)
key=ob.data.shape_keys.key_blocks[result['shape_key']]
delta=[key.data[i].co-ob.data.vertices[i].co for i in range(len(points))]
field=read(folder/'corrective-field.json');pose_delta={r['id']:Vector(r['desired_posed_delta']) for r in field['field']}
rows=[]
for a,b in edges:
    base=(ob.data.vertices[a].co-ob.data.vertices[b].co).length
    if delta[a].length>1e-10 or delta[b].length>1e-10:
        rows.append({'edge':[a,b],'basis_length_m':base,'rest_offset_jump_m':(delta[a]-delta[b]).length,
            'rest_offset_jump_over_basis_edge':(delta[a]-delta[b]).length/base,
            'posed_offset_jump_m':(pose_delta.get(a,Vector())-pose_delta.get(b,Vector())).length,
            'crosses_field_boundary':(delta[a].length>1e-10)!=(delta[b].length>1e-10)})
assert max(v.length for v in delta)<=.004 and max(v.length for v in pose_delta.values())<=.003
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();normals=[v.normal.copy() for v in me.vertices];ev.to_mesh_clear()
bone=rig.pose.bones['sword'];root=bone.head;axis=(bone.tail-root).normalized()
handle=BVHTree.FromPolygons(sp,[t for t in st if -.112<=(sum((sp[j] for j in t),Vector())/3-root).dot(axis)<=.085],all_triangles=True)
padrows={}
for n,ids in contract['pads'].items():
    padrows[n]=[]
    for i in ids:
        hit,normal,face,gap=handle.find_nearest(points[i]);toward=(hit-points[i]).normalized()
        padrows[n].append({'id':i,'gap_m':gap,'point':list(points[i]),'normal':list(normals[i]),'normal_dot_toward':normals[i].dot(toward)})
save(folder/'field-boundary-audit.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':result['artifact'],
 'identity_objects_verified':True,'original_pads_unchanged':True,'boundary_edges':rows,
 'max_neighbor_rest_jump_m':max(r['rest_offset_jump_m'] for r in rows),'max_neighbor_jump_over_basis_edge':max(r['rest_offset_jump_over_basis_edge'] for r in rows),
 'worst20':sorted(rows,key=lambda r:-r['rest_offset_jump_over_basis_edge'])[:20],'all_fixed_pad_samples':padrows,
 'limitation':'Axial and palmar smoothstep only; alignment cutoff/clearance clamp/semantic boundary can be nonsmooth. Gradient observations are diagnostics, not global smoothness or art PASS.',
 'clearance_parameter':'0.8mm local displacement clamp reserve, not a final whole-surface clearance guarantee'})
overlay=common.line_object('r010SurfaceWireframe',[[points[a],points[b]] for a,b in edges],(.04,.12,.28),.000085)
common.render(folder,'wireframe',['palm','side']);bpy.data.objects.remove(overlay,do_unlink=True)
print('R010_SURFACE_AUDIT '+str({'candidate':name,'max_jump_mm':max(r['rest_offset_jump_m'] for r in rows)*1000,'max_jump_ratio':max(r['rest_offset_jump_over_basis_edge'] for r in rows),'third_gaps_mm':{n:sorted(r['gap_m'] for r in rows)[2]*1000 for n,rows in padrows.items()}}))
