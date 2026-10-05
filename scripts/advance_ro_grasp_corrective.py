"""Close authored-control failure and register a new coherent pad-field method."""
from datetime import datetime,timezone
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');req=read(ROOT/'requests/ro-swordsman-combo-r010.json');ledger=read(QA/'quality-ledger.json');assert len(ledger['trials'])==1
start=read(QA/'v001-start.json');res=read(QA/'v001-authored-controls/result.json');assert not res['numeric_gate'];now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: deeper authored curl creates actual handle crossing; source cannot be used for corrective.',
 'contacts':{n:r['within_2mm'] for n,r in res['contact']['pad_contacts'].items()},'sword_transverse':res['contact']['transverse_crossings_count'],
 'next_source':'Original r009 safe C-wrap retained as authored grasp selection; additional curl rejected, no automatic shape filling over intersecting pose.',
 'original_pad_normals':'Ring41/index26 outward toward handle; unchanged anatomical masks retained.','whole_scores_changed':False}
save(QA/'v001-review.json',review)
ledger['trials'].append({'id':'v001','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator actual authored grasp surface/collision review',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v001-review.json'),artifact(QA/'v001-authored-controls/result.json')],'prototype_artifacts':[res['artifact']]})
save(QA/'quality-ledger-before-v002.json',read(QA/'quality-ledger.json'))
compare=workbench.compare_quality(req,ledger,ROOT);assert not compare['blockers'],compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v001.json',compare)
save(QA/'v002-start.json',{'id':'v002','started_utc':now.isoformat(),'source':clock['local_source'],'contract':artifact(QA/'local-contract.json'),
 'hypothesis':'Broad distal pulp inflation in a safe authored C-wrap supplies missing distributed surface contact without extra bone curl or changing fixed measurement IDs.',
 'change':'Single2.2mmmaximum posed normal field over full ring/index palmar branch, tapered proximally; surface safety clips only toward actual handle at0.8mmclearance. Inverse verified LBS into additive shape key. All otherdigits/palm/thumb/wrist fixed.',
 'maximum_requested_posed_m':.0022,'minimum_clearance_m':.0008,'branches':['finger2','finger4'],'prior_candidates_used':1,'new_credits':0,
 'field':'All original semantic-body points; axial smoothstep(.20,.65) and rest normal palmar smoothstep(0,.5); no nearest-three guide selection.',
 'shape_key_name':'SK_RO_GraspPulp_Corrective','basis_source_unchanged':True})
print('R010_V002_REGISTERED')
