"""Close v002 function failure, freeze v003 independent controls and actual sword."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r008'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
ledger=read(QA/'quality-ledger.json');request=read(ROOT/'requests/ro-swordsman-combo-r008.json');clock=read(QA/'phase-start.json')
start=read(QA/'v002-start.json');result=read(QA/'v002-direction/result.json');function=read(QA/'v002-functional-curl/result.json')
assert len(ledger['trials'])==2 and result['direction_gate'] and not function['numeric_self_gate']
now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: fixed uniform largecurl createsactualfinger-to-finger andlittlefinger-to-palmcrossings',
 'small_motion':'23signed isolated,8direction checks and3combined numericdiagnostics pass only tested poses; combined.30 actually MCP.42rad',
 'functional_counts':[e['transverse_pairs'] for e in function['events']],
 'representative_scope':'closed20savedpairs:11ring-middle and9little-palm; remaining22notlocalized, no all42thumbabsenceclaim',
 'independent_review':'Existinghand_phase_review directlyinspectedimages,weights andscript; advisesindependentMCPcurl/splay underactualsword beforeUV. No fourfingerweightchange.',
 'architecture_route':'a509e757-fa76-46ad-80a3-22ff53070c84',
 'boundary_caveat':'8outsideboundarypoints have actualfourfingerweights; thumbsolverprojectedhandboundary approximate; full16boneL1nowrecorded.',
 'section_caveat':'Polygonedge/convexhull notvolumeacceptance; nonplanarquad can disagreewithactualtriangles. No volumePASS.',
 'material_FAIL':16,'grip_pass':False,'whole_scores_changed':False,'new_credits':0}
save(QA/'v002-review.json',review)
ledger['trials'].append({'id':'v002','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],
 'reviewer':'Coordinator actual largecurl views/readbacks plusrequiredindependent architecture review','hypothesis':start['hypothesis'],'change':start['change'],
 'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v002-review.json'),artifact(QA/'v002-functional-curl/result.json'),artifact(QA/'v002-failure-locations/locations.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v003.json',read(QA/'quality-ledger.json'))
comparison=workbench.compare_quality(request,ledger,ROOT);assert not comparison['blockers'],comparison
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v002.json',comparison)
templates=[{'id':'shallow','finger1':[.40,.75,.45],'finger2':[.65,.95,.55],'finger3':[.70,1.00,.55],'finger4':[.65,.95,.55],'thumb':[.25,.65,.35],'pronation':.40},
 {'id':'wrap','finger1':[.55,1.00,.65],'finger2':[.80,1.20,.70],'finger3':[.85,1.25,.75],'finger4':[.80,1.20,.70],'thumb':[.30,.80,.40],'pronation':.50},
 {'id':'distalwrap','finger1':[.45,1.15,.80],'finger2':[.65,1.35,.85],'finger3':[.70,1.40,.90],'finger4':[.70,1.35,.85],'thumb':[.25,.95,.55],'pronation':.60}]
plan={'id':'v003','started_utc':now.isoformat(),'source':result['artifact'],'weapon':artifact(QA/'weapon-probe/actual-weapon.json'),
 'hypothesis':'Independentdigitcurl andsmallMCPsplay avoidobserveduniformcrossing whileformingactualhandlecontact',
 'change':'Onlyposecontrols plusboundedfixedrigidweaponplacement; geometry,bones16positions,UV,weights preserved. Addexactweaponboneforcontacts.',
 'budget':clock['budget'],'candidate_limit':4,'previous_candidates_used':2,'new_credits':0,
 'templates':templates,'splay_radians':{'finger1':.05,'finger2':.02,'finger3':-.02,'finger4':-.04},
 'MCP_splay_axis':'Fixedpalmnormal (0,-1,0), positive spreads littlefinger toward-X; compose splaythenflexion; noPIP/DIPsidebend',
 'weapon_shifts':[{'id':'palm','translation':[0,-.020,-.024]},{'id':'distal','translation':[0,-.015,-.014]}],
 'maximum_full_grip_cases':6,'littlefinger_isolated_cases':[[.30,.60,.40],[.40,.75,.45],[.45,1.15,.80],[.55,1,.65],[.80,1.05,.60]],
 'fixed_masks':'r007/v003 source five namedpalmar pads unchanged; actualswordhandle andwholetriangle tests',
 'contact_required':'Eachdigit3distinctfrozenpadpoints<=2mm; whole-surface penetration<=1mm, unknown0, transverse0, selfcross0, visualpadopposition. Openapproachonlycollisiongate.',
 'stop':'NoUVonfailure; do not alterfourfingerweights orbonecenters; no angle-onlyzerocollision success.'}
save(QA/'v003-start.json',plan)
print('R008_V003 independentactualsword6cases registered')
