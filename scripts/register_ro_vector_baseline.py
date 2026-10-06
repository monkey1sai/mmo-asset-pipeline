"""Prospective local contract and fresh whole baseline; no old ledger writes."""
from datetime import datetime, timezone
import copy
import hashlib
import shutil
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
from ro_review_common import render_views
import workbench

clock=read(QA/'phase-start.json')
request=read(ROOT/'requests/ro-swordsman-combo-r008.json')
probe=read(QA/'source-probe/probe.json')
mesh=read(QA/'source-probe/mesh-and-weights.json')
old_masks=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')
points=[Vector(p) for p in mesh['geometry']['points']]
h=Vector(mesh['bone_points']['thumb_01']['head'])
ip=Vector(mesh['bone_points']['thumb_03']['head'])
tip=Vector(mesh['bone_points']['thumb_03']['tail'])
axis=(tip-ip).normalized()
fourfinger=sorted(int(i) for i,r in old_masks['semantic'].items() if r['branch']!='thumb')
cap=sorted(i for i,p in enumerate(points) if mesh['geometry']['point_attributes']['r007_source_point_id'][i]==0 and (p-ip).dot(axis)>.0095294)
assert cap==old_masks['cap_rigid_vertices']
domain=sorted(i for i,p in enumerate(points) if i not in fourfinger and p.z>h.z-.023 and p.x>h.x-.025)
neighbors={i:set() for i in range(len(points))}
for a,b in mesh['geometry']['edges']:
    neighbors[a].add(b);neighbors[b].add(a)
outside=set(range(len(points)))-set(domain)
components=[];todo=set(domain)
while todo:
    component=set();stack=[next(iter(todo))]
    while stack:
        i=stack.pop()
        if i in component or i not in todo:continue
        component.add(i);stack.extend(neighbors[i])
    todo-=component
    anchors=(set().union(*(neighbors[i] for i in component))&outside)|(component&set(cap))
    assert anchors,'Every domain component must meet boundary/cap anchors'
    components.append({'points':sorted(component),'boundary_or_cap_anchors':sorted(anchors)})
contract={'source':clock['local_baseline_source'],'source_probe':artifact(QA/'source-probe/probe.json'),
 'geometry':artifact(QA/'source-probe/mesh-and-weights.json'),'geometry_UV_and_bone_positions_frozen':True,
 'fourfinger_protected_ids':fourfinger,'anatomical_domain_ids':domain,'domain_components':components,
 'domain_rule':'Connected thumb/thenar graph excluding frozen fourfinger. Rest Z > CMC.z-23mm, X > CMC.x-25mm; no weight-based exclusion.',
 'cap_rigid_ids':cap,'cap_rule':'New patch source_id==0 and IP-to-tip axial>9.5294mm, including four distal extraordinary points; fixed thumb03 only.',
 'joint_positions':mesh['bone_points'],'skin_method':'Linear blend; no preserve volume change during vector experiment',
 'test_parameters':isolated_parameters(),'combined_joint_factors':[1,1.4,.85],
 'opposition_axis':'Thumb01 longitudinal axis; signed palmar pad displacement toward ulnar(-X) verified separately before any grip.',
 'required_views':VIEWS,'resolution':[1280,1280],'lighting':'Inherited from exact same local source file, saved per baseline; gray for function, no effects.',
 'local_stop':'Any transverse crossing/degenerate or visible thenar/web/cap collapse; normalized weights alone cannot pass; grip held until signed isolated and combined visible checks pass.',
 'diagnostic_metrics':'Full L1/L2 vector jumps, absolute edge length changes, ratios and actual polygon sections. Section enclosure alone is not volume proof.',
 'known_material_failure':{'mixed_source_UV_faces':16,'rebake_permitted_only_after_function':True},
 'whole_character_acceptance':'Separate complete300frames/60fps/left/grip/assembly/VFX/freshanimatedGLB required; local success does not increase wholequalityscores.'}
save(QA/'local-contract.json',contract)
folder=QA/'baseline';out=ROOT/'assets/processed/ro-swordsman-combo-r008/baseline'
assert not folder.exists() and not out.exists();folder.mkdir();out.mkdir(parents=True)
source=ROOT/clock['baseline_source']['path']
for suffix in ['.blend','.glb']:
    src=source.with_suffix(suffix);dest=out/('ro_weight_vector_baseline'+suffix)
    shutil.copyfile(src,dest);assert src.read_bytes()==dest.read_bytes()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
render_views(folder,frame=1)
rig=bpy.data.objects['ARM_RO_Swordsman']
triangles=0;invalid=0;max_influences=0
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not ob.name.startswith('SM_RO_'):continue
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();me.calc_loop_triangles();triangles+=len(me.loop_triangles);ev.to_mesh_clear()
    for v in ob.data.vertices:
        ww=[g for g in v.groups if g.weight>1e-8];max_influences=max(max_influences,len(ww))
        invalid+=not ww or len(ww)>4 or abs(sum(g.weight for g in ww)-1)>1e-5 or any(ob.vertex_groups[g.group].name not in rig.data.bones for g in ww)
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':clock['baseline_source'],
 'actual_fresh_fixed_views':True,'whole_triangles':triangles,'bones':len(rig.data.bones),
 'maximum_influences':max_influences,'invalid_weights':invalid,
 'local_new_signed_pose_readbacks':artifact(QA/'source-probe/probe.json'),
 'saved_interval_contact_evidence':'Historical hash-bound r007 same byte-identical baseline; not rerun or newlypassed.',
 'source_geometry_changed':False,'full300_skills_and_effects_present':False,'art_verdict':'NO_SHIP',
 'artifacts':[artifact(p) for p in sorted(out.glob('*'))]}
save(folder/'baseline.json',report)
old=read(ROOT/'runs/qa/ro-swordsman-combo-r007/quality-ledger.json')['trials'][0]
trial=copy.deepcopy(old);now=datetime.now(timezone.utc)
trial.update(started_utc=clock['baseline_started_utc'],ended_utc=now.isoformat(),elapsed_seconds=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds())
trial['reviewer']='Coordinator fresh whole views and24signed local evaluated readbacks; historical closed interval evidence explicitly hash-bound'
trial['previews']={n:artifact(folder/(n+'.png')) for n in request['quality']['protocol']['views']}
trial.pop('waiting_time_accounting',None)
evidence=trial['evidence'];evidence.update(request_id=request['id'],request_sha256=workbench.request_sha256(request),local_gate_contract=artifact(QA/'local-contract.json'),deliverables=report['artifacts'],subject_artifacts=report['artifacts'])
for row in evidence['checks'].values():row['artifacts']+=[artifact(folder/'baseline.json')]
ledger={'schema_version':1,'request_id':request['id'],'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'local_gate_contract':artifact(QA/'local-contract.json'),'trials':[trial],'phase_history':request['phase_history']}
result=workbench.compare_quality(request,ledger,ROOT);assert not result['blockers'],result
save(folder/'evidence.json',evidence);save(QA/'quality-ledger.json',ledger);save(QA/'comparison-baseline.json',result)
save(QA/'v001-start.json',{'id':'v001','started_utc':now.isoformat(),'budget':clock['budget'],
 'source':clock['local_baseline_source'],'contract':artifact(QA/'local-contract.json'),
 'hypothesis':'Complete fourcomponent screened harmonic vectors remove hand-to-thumb02 boundary while cap andfourfinger remain fixed.',
 'change':'600 fixed Jacobi iterations, relaxation0.7, fidelity0.35; smooth axial joint targets with16/10/6mm root/MCP/IP halfwidths; no parameter variants in v001.',
 'new_credits':0,'previous_candidates_used':0,'candidate_limit':4})
print('R008_BASELINE '+json.dumps({'triangles':triangles,'bones':len(rig.data.bones),'anchors':len(cap),'domain':len(domain),'candidate_started':'v001','scores_changed':False}))
