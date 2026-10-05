"""Record the actually reviewed new baseline before any candidate repair."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1]; ID='ro-swordsman-combo-r002'; QA=ROOT/'runs/qa'/ID
def artifact(relative):
    p=(ROOT/relative).resolve(strict=True)
    if ROOT not in p.parents: raise ValueError('Path escape')
    return {'path':relative,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (QA/'quality-ledger.json').exists(): raise RuntimeError('Baseline already recorded; cannot reset')
request=workbench.read_json(ROOT/'requests'/f'{ID}.json'); start=workbench.read_json(QA/'phase-start.json')
fresh=workbench.read_json(QA/'baseline/fresh-import.json')
assert fresh['bones']==0 and fresh['skin_count']==0 and fresh['animations']==[] and fresh['external_dependencies']==[]
assert abs(fresh['bind_bounds_blender_m']['max'][2]-1.74)<1e-5 and abs(fresh['bind_bounds_blender_m']['min'][2])<1e-5
review={'reviewer':'Independent quality_review task, read-only actual new five PNGs and source-reference comparison', 'viewed':['front','side','back','three-quarter','detail'],'not_claimed':'No deformation poses executed on a zero-bone source; actual absence inspected and marked fail.', 'scores':{'design-intent':{'value':3,'reason':'Brown spiky male/silver plates/navy tails/leather readable; dark metallic front panel, closed eyes and fused weapon miss requirements'},'silhouette':{'value':3,'reason':'Five-view major silhouette intact; fused waist/hand/scabbard and connected rear cloth lack separation'},'form-proportion':{'value':3,'reason':'Main volumes credible; angular face and wrist/belt/scabbard joints unclear'},'materials':{'value':2,'reason':'Wrong dark metal tabard, crumpled-foil armor, light hair and eye artifacts'},'craft':{'value':2,'reason':'Intact static surfaces but fused moving parts and face/eye defects'},'use-readability':{'value':0,'reason':'0 rig/animations/effects; required five skill stages and continuous movement absent'}}}
save(QA/'baseline/independent-review.json',review)
inspect=artifact(f'runs/qa/{ID}/baseline/inspection.json'); rv=artifact(f'runs/qa/{ID}/baseline/independent-review.json'); fi=artifact(f'runs/qa/{ID}/baseline/fresh-import.json')
content=[artifact(f'assets/processed/{ID}/baseline/{f}') for f in ['ro_source_baseline.blend','ro_source_baseline.glb']]
readme=artifact(f'assets/processed/{ID}/baseline/README.md')
checks={}
for c in workbench.required_checks(request):
    key=c['id']; passed=key in {'scale_pivot','package_complete'}
    methods={'scale_pivot':'Actual fresh import bounds verify1.74m height and ground origin, Blender Z-up/-Y forward converted to GLB Y-up/Z-forward; XY planning only', 'package_complete':'Actual .blend/.glb/README files and all embedded dependencies reviewed as a baseline package; not a final accepted delivery', 'export-roundtrip':'Fresh import retains static mesh/materials, but required skin/channels cannot be checked because absent; explicit failure', 'deformation':'Actual source has zero bones and fused limbs/weapon; required deformation capability absent, not an executed pose test'}
    checks[key]={'status':'pass' if passed else 'fail','method':methods.get(key,'Actual independent fixed-view inspection and DCC inventory: '+key+' requirement absent or visibly defective; see review'),'artifacts':[inspect,rv,fi]+([readme] if key=='package_complete' else [])}
evidence={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'checks':checks,'deliverables':content+[readme],'subject_artifacts':content}
end=datetime.now(timezone.utc); started=datetime.fromisoformat(start['baseline_started_utc'])
trial={'id':'baseline','parent_id':None,'status':'completed','started_utc':started.isoformat(),'ended_utc':end.isoformat(),'elapsed_seconds':(end-started).total_seconds(),'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'previews':{v:artifact(f'runs/qa/{ID}/baseline/{v}.png') for v in request['quality']['protocol']['views']},'scores':review['scores'],'evidence':evidence}
ledger={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'trials':[trial],'previous_phase_preserved':request['phase_history'],'clock_policy':start['time_accounting']}
result=workbench.compare_quality(request,ledger)
assert not result['blockers'],result
save(QA/'baseline/evidence.json',evidence); save(QA/'quality-ledger.json',ledger); save(QA/'comparison-baseline.json',result)
save(QA/'v001-start.json',{'id':'v001','started_utc':end.isoformat(),'parent_id':'baseline','hypothesis':'Explicit planar source surface selections plus rebuilt quad-loop joints, grasping hands and split cloth can remove fused-pose artifacts while preserving character identity.', 'change':'Replace the source fused moving structure with clean articulated anatomy/clothing/weapon; retain head, chest armor, shoulder surfaces and boots/UV. Baseline quality/protocol unchanged.', 'before_candidate_work':True})
print(json.dumps(result,ensure_ascii=False))
