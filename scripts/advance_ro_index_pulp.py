"""Preserve v002 failure and prospectively register a full-pad amplitude revision."""
from datetime import datetime,timezone
from pathlib import Path
import copy,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');req=read(ROOT/'requests/ro-swordsman-combo-r010.json');ledger=read(QA/'quality-ledger.json');assert len(ledger['trials'])==2
start=read(QA/'v002-start.json');res=read(QA/'v002-pulp-corrective/result.json');assert not res['numeric_gate'];now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: original index pad has only2contacts; fullpulp corrective otherwise conservatively admissible, no whole acceptance.',
 'contacts':{n:r['within_2mm'] for n,r in res['contact']['pad_contacts'].items()},'self':res['self']['transverse_pairs'],'sword':res['contact']['transverse_crossings_count'],
 'new_evidence':'Full75point ring/index brush field improves ring contact3/index2 withouttestedcrossing; originalwidth/shape visibly preserved. Next only wholeindex amplitude, same geometry/support/clearance/pose.',
 'whole_scores_changed':False,'interval_not_run':'Static contact prerequisite failed'}
save(QA/'v002-review.json',review)
ledger['trials'].append({'id':'v002','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator fullfield skin roundtrip, originalshape/collision/contact andgrayviews',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v002-review.json'),artifact(QA/'v002-pulp-corrective/result.json')],'prototype_artifacts':[res['artifact']]})
save(QA/'quality-ledger-before-v003.json',read(QA/'quality-ledger.json'));compare=workbench.compare_quality(req,ledger,ROOT);assert not compare['blockers'],compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v002.json',compare)
code=ROOT/'scripts/build_ro_grasp_corrective.py';text=code.read_text(encoding='utf-8')
replacements={"v002-start.json":"v003-start.json","v002-pulp-corrective":"v003-index-pulp","R010_V002":"R010_V003", "amount=start['maximum_requested_posed_m']*smoothstep":"amount=start['maximum_requested_by_branch_m'][branch]*smoothstep"}
for old,new in replacements.items():
    assert text.count(old)==(2 if old=='v002-pulp-corrective' else 1),(old,text.count(old))
    text=text.replace(old,new)
derived=ROOT/'scripts/build_ro_index_pulp.py'
with derived.open('x',encoding='utf-8') as f:f.write(text)
save(QA/'v003-code-derivation.json',{'source':artifact(code),'derived':artifact(derived),'replacements':replacements,'old_code_preserved':True})
plan=copy.deepcopy(start);plan.update(id='v003',started_utc=now.isoformat(),prior_candidates_used=2,
 maximum_requested_by_branch_m={'finger2':.0022,'finger4':.0028},
 hypothesis='Index fullpulp needs slightlylargerboundednormalfield; ring already meetsfixedcontact, leaveunchanged. Actualsurfaceguard decides, not assumptions.',
 change='Same fullanatomicalsurfacefield andsafeCwrap, ring2.2mm/index2.8mm maxima, inverseLBS andunchanged0.8mmclearance; no nearestpoint selection ormaskchange.',
 derivation=artifact(QA/'v003-code-derivation.json'))
save(QA/'v003-start.json',plan)
print('R010_V003_REGISTERED')
