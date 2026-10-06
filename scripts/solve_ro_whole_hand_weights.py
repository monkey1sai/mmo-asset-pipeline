"""One frozen fourfinger vector candidate; original grip remains fixed."""
from datetime import datetime,timezone
from pathlib import Path
import sys,json,bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import contacts
from ro_core_rig import assign
from supported_weight_solver import solve_supported
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
clock=read(QA/'phase-start.json');start=read(QA/'v001-start.json');contract=read(QA/'local-contract.json')
folder=QA/'v001-vectors';out=ROOT/'assets/processed/ro-swordsman-combo-r009/v001-vectors'
folder.mkdir();out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source'] and artifact(QA/'local-contract.json')==start['contract']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
common.reset(rig);rest=common.geometry(ob);original=common.weights(ob);points=[Vector(p) for p in rest['points']]
names=['hand']+[f'{n}_{j:02}' for n in ['finger1','finger2','finger3','finger4','thumb'] for j in range(1,4)]
indices={n:i for i,n in enumerate(names)}
supports={int(i):{indices[n] for n in rows} for i,rows in contract['supports'].items()}
domain=set(supports);targets=[];initial=[]
chains={n:[rig.data.bones[f'{n}_{j:02}'].head_local.copy() for j in range(1,4)]+[rig.data.bones[f'{n}_03'].tail_local.copy()] for n in ['finger1','finger2','finger3','finger4']}
smooth=lambda t:max(0,min(1,t))**2*(3-2*max(0,min(1,t)))
for i,p in enumerate(points):
    vector=[original[i].get(n,0) for n in names];mass=sum(vector);assert abs(mass-1)<1e-5
    initial.append([x/mass for x in vector]);target=[0.]*len(names)
    role=contract['semantic_roles'].get(str(i))
    if role and role['role']=='finger_body':
        n=role['branch'];s=contract['rest_branch_coordinates'][str(i)][n]['axial_m'];lengths=[(b-a).length for a,b in zip(chains[n],chains[n][1:])]
        root=smooth((s+.016)/.032);j1=smooth((s-lengths[0]+.010)/.020);j2=smooth((s-sum(lengths[:2])+.006)/.012)
        values=[1-root,root*(1-j1),root*j1*(1-j2),root*j1*j2]
        for name,value in zip(['hand']+[f'{n}_{j:02}' for j in range(1,4)],values):target[indices[name]]=value
    elif role:
        contributions={}
        for n in role['branches']:
            row=contract['rest_branch_coordinates'][str(i)][n]
            contributions[n]=smooth((row['axial_m']+.016)/.032)*smooth((.024-row['radial_m'])/.020)
        total=sum(contributions.values());scale=max(1,total)
        target[0]=1-total/scale
        for n,value in contributions.items():target[indices[n+'_01']]=value/scale
    else:target=initial[-1][:]
    targets.append(target)
anchors={}
for n,ids in contract['fourfinger_rigid_caps'].items():
    for i in ids:
        row=[0.]*len(names);row[indices[n+'_03']]=1;anchors[i]=row
graph={i:[] for i in range(len(points))}
for a,b in rest['edges']:
    weight=1/max((points[a]-points[b]).length,1e-6);graph[a].append((b,weight));graph[b].append((a,weight))
solved,stats=solve_supported(initial,targets,graph,domain,supports,anchors,**contract['solver'])
for i in sorted(domain):assign(ob,ob.data.vertices[i],dict(zip(names,solved[i])))
ww=common.weights(ob)
assert common.geometry(ob)==rest
assert all(ww[i]==original[i] for i in set(range(len(points)))-domain)
assert all(len(row)<=4 and abs(sum(row.values())-1)<1e-5 for row in ww.values())
assert all(set(ww[i])<=set(contract['supports'][str(i)]) for i in domain)
error=max(abs(ww[i].get(n,0)-solved[i][k]) for i in domain for k,n in enumerate(names))
save(folder/'weights.json',{'original':original,'final':ww,'target':targets,'solver':stats,'maximum_assign_float_error':error,
                           'domain':sorted(domain),'caps':contract['fourfinger_rigid_caps'],'thumb203_exact':True,'geometry_UV_bones_exact':True})
saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(common.material('r009V1Gray',(.55,.55,.55)))
sword.hide_render=True;events=[]
for n in ['finger1','finger2','finger3','finger4']:
    for j in range(1,4):
        for angle in [.05,.30]:
            label=f'{n}-{j:02}-{angle:.2f}';params=[{'bone':f'{n}_{j:02}','angle':angle,'mode':'flexion'}]
            event,pts=common.actual(ob,rig,rest,label,params,ww);events.append(event)
    common.render(folder,n+'-03-0.30',['side'])
for n,m in read(QA/'baseline/local-baseline.json')['basis'].items():rig.pose.bones[n].matrix_basis=Matrix(m)
bpy.context.view_layer.update();sword.hide_render=False
params=read(ROOT/'runs/qa/ro-swordsman-combo-r008/v004-contact-solver/result.json')['controls']
fixed,pts=grip.capture(ob,rig,rest,'same-r008-selected-grip',params,ww)
pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']
contact=contacts(ob,sword,rig,pads,'same-r008-selected-grip',{'no_search_or_weapon_change':True})
common.render(folder,'same-grip')
save(folder/'same-grip-points.json',{'points':[list(p) for p in pts]})
edge_rows=[]
for a,b in [(277,278),(372,388)]:
    base=(points[a]-points[b]).length;length=(pts[a]-pts[b]).length
    edge_rows.append({'edge':[a,b],'rest_m':base,'posed_m':length,'ratio':length/base,'weights':[ww[a],ww[b]],
                     'full_bone_L1':sum(abs(ww[a].get(n,0)-ww[b].get(n,0)) for n in names)})
ob.data.materials.clear()
for m in saved:ob.data.materials.append(m)
dest=out/'right_hand_full_vectors.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),'weights':artifact(folder/'weights.json'),
 'events':events,'same_grip_self':fixed,'same_grip_contact':contact,'fixed_problem_edges':edge_rows,
 'geometry_UV_bones_controls_weapon_fixed':True,'thumb203_exact':True,'shape_gate':'pending actual visualreview, metrics diagnosticonly',
 'static_numeric_gate':contact['surface_gate_pass'] and fixed['transverse_pairs']==0,'whole_quality_changed':False,'new_credits':0,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))],'raw_posed_points':artifact(folder/'same-grip-points.json')}
save(folder/'result.json',report)
print('R009_WEIGHTS '+json.dumps({'self':fixed['transverse_pairs'],'sword':contact['transverse_crossings_count'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'edges':[(r['edge'],r['ratio']) for r in edge_rows],'minratio':fixed['minimum_edge_ratio'],'maxratio':fixed['maximum_edge_stretch']}))
