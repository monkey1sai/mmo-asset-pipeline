"""Preserve the failed reviewed phase; never turn numeric checks into art PASS."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import workbench

ROOT=Path(__file__).resolve().parents[1];ID='ro-swordsman-combo-r002';QA=ROOT/'runs/qa'/ID;V=QA/'v003';OUT=ROOT/'assets/processed'/ID/'v003'
def artifact(path):
    p=(ROOT/path).resolve(strict=True)
    if not p.is_relative_to(ROOT):raise ValueError('Path escape')
    return {'path':path,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
request=workbench.read_json(ROOT/'requests'/f'{ID}.json');ledger=workbench.read_json(QA/'quality-ledger.json')
if any(t['id']=='v003' for t in ledger['trials']):
    # Recover the assessment-only tool-name error without rewriting trial time.
    evidence=workbench.read_json(V/'delivery-review-evidence.json')
    save(QA/'assessment-final.json',workbench.assess(request,evidence))
    print('Existing candidate/clock preserved; assessment saved')
    raise SystemExit(0)
review=workbench.read_json(V/'independent-review.json');scale=workbench.read_json(V/'body-scale-rig-map.json')
assert review['decision']=='NO_SHIP' and scale['subject_unchanged']
contents=[artifact(f'assets/processed/{ID}/v003/{f}') for f in ['ro_swordsman_master.blend','ro_swordsman_combo.glb','ro_skill_effects.glb']]
readme=artifact(f'assets/processed/{ID}/v003/README.md')
assert contents[0]['sha256']==review['subjects']['master_sha256']==scale['subject_sha256'] and contents[1]['sha256']==review['subjects']['character_glb_sha256']
dependencies=[];videos=[]
for f in ['ro_swordsman_combo.glb','ro_skill_effects.glb']:
    raw=(OUT/f).read_bytes();length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
    doc=json.loads(raw[20:20+length]);external=[x['uri'] for group in ['buffers','images'] for x in doc.get(group,[]) if x.get('uri') and not x['uri'].startswith('data:')]
    assert not external;dependencies.append({'file':f,'external_dependencies':external,'skin_count':len(doc.get('skins',[])),'animation_count':len(doc.get('animations',[]))})
for label,name in [('neutral-master-final','ro_swordsman_neutral.mp4'),('neutral-roundtrip-final','ro_swordsman_roundtrip.mp4'),('with-effects-final','ro_swordsman_effects.mp4')]:
    path=V/label/name
    result=subprocess.run([r'C:\Windows\ffmepg\bin\ffprobe.exe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames,duration','-of','json',str(path)],check=True,capture_output=True,text=True)
    stream=json.loads(result.stdout)['streams'][0];assert stream['r_frame_rate']=='60/1' and stream['nb_frames']=='300' and stream['duration']=='5.000000'
    assert len(list((V/label/'frames').glob('frame_*.png')))==300
    videos.append({'file':artifact(path.relative_to(ROOT).as_posix()),'ffprobe':stream})
manifest={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'status':'local_review_package_failed_not_delivered','files':contents+[readme],'embedded_dependencies':dependencies,'videos':videos,'known_limitations':review['hard_findings'],'git':'not_staged_not_committed_not_pushed','source':'assets/raw/ro-swordsman-combo/rodin-v001/base_basic_pbr.glb'}
save(V/'review-package-manifest.json',manifest)
reports=[artifact(f'runs/qa/{ID}/v003/{f}') for f in ['independent-review.json','fresh-import.json','body-scale-rig-map.json','review-package-manifest.json','neutral-master-final/report.json','neutral-roundtrip-final/report.json','with-effects-final/report.json']]
checks={}
for check in workbench.required_checks(request):
    key=check['id'];status=review['checks'][key]
    if key=='scale_pivot':status='fail' # Observed1.737322m vs specified nominal1.74; no approved tolerance claim.
    if key=='package_complete':status='pass'
    methods={'scale_pivot':'Actual evaluated REST body-only height1.737321855m, ground~-1.7e-9m and root0; nominal1.74m differs2.678mm, no approved tolerance/exact size acceptance. Bone pivots explicitly mapped; failed posed feet remain separate.', 'package_complete':'Actual three requested model artifacts, README rig/axis/time/effect mapping, manifest/readback hashes, bothGLBs no externalbuffers/images, and threeffprobe60fps/300frames/5s videos. Complete local failed review package, not accepted delivery.', 'rig_mapping':'Actual freshGLB25named joints/1skin/75channels, mapped local bone heads/tails and bindings; no game retarget claim.'}
    checks[key]={'status':status,'method':methods.get(key,'Actual independent fixed-view/all300thumbnail/selectedfullframe review plus current-subject DCC reports: '+key+' failed for findings in independent-review; no claimed game/runtime test.'),'artifacts':reports}
evidence={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'checks':checks,'deliverables':contents+[readme],'subject_artifacts':contents}
start=workbench.read_json(QA/'v003-start.json');end=datetime.now(timezone.utc)
trial={**start,'status':'completed','ended_utc':end.isoformat(),'elapsed_seconds':(end-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer']+'; coordinator completed scale/package measurements and manifest checks after independent art review','scores':review['scores'],'previews':{v:artifact(f'runs/qa/{ID}/v003/{v}.png') for v in request['quality']['protocol']['views']},'evidence':evidence,'intra_trial_attempts':['attempt01 eye reconstruction','attempt02-overbudget60780 triangles','attempt03-motion28headoverlap frames','final all300 reports retain footsliding/floating/handjump/export differences']}
ledger['trials'].append(trial);comparison=workbench.compare_quality(request,ledger)
assert not comparison['blockers'],comparison
assert comparison['trials'][-1]['decision']=='discard' and comparison['next_action']=='stop_budget',comparison
save(V/'evidence.json',evidence);save(QA/'quality-ledger.json',ledger);save(QA/'comparison-final.json',comparison)
evidence['quality_ledger']=artifact(f'runs/qa/{ID}/quality-ledger.json')
save(V/'delivery-review-evidence.json',evidence);save(QA/'assessment-final.json',workbench.assess(request,evidence))
print(json.dumps(comparison,ensure_ascii=False));print('NO_SHIP all3 candidates preserved; no more r002 revisions')
