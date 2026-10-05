"""Isolate the saved half-frame ray ambiguity without modifying a candidate."""
from pathlib import Path
from datetime import datetime,timezone
import sys,bpy,numpy as np,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
from ro_hand_gate import evaluated,sword_solid
from ro_world_grasp_gate import world_contacts
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
res=read(QA/'v003-local-animation/result.json');assert res['first_failure']['frame']==46.5
assert artifact(ROOT/res['artifact']['path'])==res['artifact']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/res['artifact']['path']),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.frame_set(46,subframe=.5);bpy.context.view_layer.update()
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
pads=read(QA/'local-contract.json')['pads'];contact=world_contacts(ob,sword,rig,pads,'saved46.5',{})
points,tris,edges=evaluated(ob);sp,st,tree=sword_solid(sword)
samples={'vertex':points,'face':[sum((points[i] for i in t),Vector())/3 for t in tris],'edge':[(points[a]+points[b])/2 for a,b in edges]}
vertex_keys=[tuple(round(float(c),6) for c in p) for p in sp]
directed={}
for t in st:
    for a,b in zip(t,t[1:]+t[:1]):
        x,y=vertex_keys[a],vertex_keys[b];key=tuple(sorted([x,y]));directed.setdefault(key,[]).append((x,y))
orientation_bad=[k for k,rows in directed.items() if len(rows)!=2 or rows[0]!=tuple(reversed(rows[1]))]
rows=[]
for kind,i,reason in contact['unknown_inside']:
    p=samples[kind][i];v=np.array([[list(sp[j]-p) for j in t] for t in st])
    a,b,c=v[:,0],v[:,1],v[:,2];la,lb,lc=np.linalg.norm(a,axis=1),np.linalg.norm(b,axis=1),np.linalg.norm(c,axis=1)
    determinant=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
    winding=float(np.sum(2*np.arctan2(determinant,denominator))/(4*math.pi))
    rows.append({'kind':kind,'index':i,'reason':reason,'point':list(p),'nearest_m':tree.find_nearest(p)[3],'solid_angle_winding':winding,'original_unknown_preserved':True})
save(QA/'v003-local-animation/ray-ambiguity-diagnosis.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'subject':res['artifact'],
 'reproduced_unknowns':contact['unknown_inside'],'self_or_sword_failure_not_proven':True,'welded_oriented_edges_bad':len(orientation_bad),'unknown_sample_diagnosis':rows,
 'method':'Double precision signed solid-angle winding over all actual sword triangles, diagnostic only; original failed half-frame and zero-unknown gate preserved.',
 'geometry_or_animation_changed':False})
print(json.dumps({'unknown':contact['unknown_inside'],'orientation_bad':len(orientation_bad),'diagnosis':rows}))
