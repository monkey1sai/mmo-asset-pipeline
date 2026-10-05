"""Count the failed ray interval and register last method-only candidate."""
from datetime import datetime,timezone
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');req=read(ROOT/'requests/ro-swordsman-combo-r010.json');ledger=read(QA/'quality-ledger.json');assert len(ledger['trials'])==3
start=read(QA/'v003-start.json');res=read(QA/'v003-local-animation/result.json');diagnosis=read(QA/'v003-local-animation/ray-ambiguity-diagnosis.json')
assert not res['interval_numeric_pass'] and res['first_failure']['frame']==46.5 and diagnosis['welded_oriented_edges_bad']==0
now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP','classification':'TEST_FAILURE: two-ray parity leaves wrist edge unknown at46.5 despite distance65.56mm and complete oriented-solid winding~0; originalintervalfailed remains.',
 'static_corrective_numeric_pass':True,'original_interval_samples':121,'original_interval_failures':1,'original_first_failure':res['first_failure'],
 'diagnosis':artifact(QA/'v003-local-animation/ray-ambiguity-diagnosis.json'),'whole_scores_changed':False,
 'shape_not_rebuilt':'nextmethod keeps byteidentical animatedsource andallthresholds; supplement unknown classification only, no geometry/curve improvement claim.'}
save(QA/'v003-review.json',review)
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator endpoint+121actualbakedframes andsaveduncertainty diagnosis',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],
 'supporting_reports':[artifact(QA/'v003-review.json'),artifact(QA/'v003-local-animation/result.json')],'prototype_artifacts':[read(QA/'v003-index-pulp/result.json')['artifact'],res['artifact']]})
save(QA/'quality-ledger-before-v004.json',read(QA/'quality-ledger.json'));compare=workbench.compare_quality(req,ledger,ROOT);assert not compare['blockers'],compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v003.json',compare)
save(QA/'v004-start.json',{'id':'v004','started_utc':now.isoformat(),'source':res['artifact'],'contract':artifact(QA/'local-contract.json'),
 'hypothesis':'Conservative closed-oriented-solid classification resolves a numerical ray ambiguity without changing actual shape, pose or acceptance thresholds.',
 'change':'Only supplemental classification of original unknown rays: winding0/abs1 within1e-7, nearest>=1um andclosedorientationverified, elseunknown retained; originalreports separatelysaved.',
 'original_unknown_gate':0,'method_change_recorded':True,'geometry_animation_unchanged':True,'prior_candidates_used':3,'last_candidate':True,'new_credits':0,
 'expected_points':res['expected_points'],'no_clock_reset':True})
print('R010_V004_LAST_METHOD_CANDIDATE_REGISTERED')
