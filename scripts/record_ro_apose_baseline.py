"""Persist independent raw-baseline review before the one authorized local trial."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT = Path(__file__).resolve().parents[1]
ID = 'ro-swordsman-combo-r003'
QA = ROOT / 'runs/qa' / ID

def save(path, value):
    if path.exists():
        raise ValueError('Preserve prior record: ' + path.name)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def artifact(relative):
    path = (ROOT / relative).resolve(strict=True)
    if not path.is_relative_to(ROOT):
        raise ValueError('Path escape')
    return {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

request = workbench.read_json(ROOT/'requests'/f'{ID}.json')
start = workbench.read_json(QA/'phase-start.json')
inspection = workbench.read_json(QA/'baseline/inspection.json')
fresh = workbench.read_json(QA/'baseline/fresh-import.json')
assert fresh['bones']==0 and fresh['skin_count']==0 and fresh['animations']==[] and fresh['external_dependencies']==[]
assert abs(fresh['bind_bounds_blender_m']['max'][2]-1.74)<1e-5 and abs(fresh['bind_bounds_blender_m']['min'][2])<1e-5
review = {'reviewer': 'Independent quality_review task; actual five PNGs, new design and original action sheet',
          'viewed': request['quality']['protocol']['views'],
          'scores': {
              'design-intent': {'value': 3, 'reason': 'Hair, male anime face, armor and colors match; required sword absent and facial linework blurred.'},
              'silhouette': {'value': 3, 'reason': 'Clear arm/torso separation and front/3Q; rear coat bell is thick and lacks separate articulated panels.'},
              'form-proportion': {'value': 3, 'reason': 'Credible main body volumes; thick hair, flat facial transition and thick coat hem need refinement.'},
              'materials': {'value': 3, 'reason': 'Metal/cloth/leather readable and three embedded maps loaded; eye smear, rough plate-edge marks and patchy shoulder highlights.'},
              'craft': {'value': 2, 'reason': 'Static source improved but hair/eyes/armor edges imperfect; eight nonmanifold edges unlocalized and no functional articulation.'},
              'use-readability': {'value': 0, 'reason': 'No sword, rig, sequence or effects.'}},
          'limits': 'Visual baseline only; numeric mesh facts from actual coordinator Blender inspection, no animated deformation inferred.'}
save(QA/'baseline/independent-review.json', review)
out = ROOT/'assets/processed'/ID/'baseline'
save(out/'README.json', {'status': 'source_baseline_not_delivery', 'source': inspection['source'], 'source_sha256': inspection['source_sha256'],
                        'edit_scope': 'metric normalization only; no rig, geometry repair, animation or effects', 'height_m': 1.74, 'embedded_texture_count': 3, 'git': 'held'})
content = [artifact(f'assets/processed/{ID}/baseline/{name}') for name in ['ro_source_baseline.blend','ro_source_baseline.glb']]
support = [artifact(f'runs/qa/{ID}/baseline/{name}') for name in ['inspection.json','fresh-import.json','independent-review.json']]
checks = {}
for check in workbench.required_checks(request):
    key = check['id']
    methods = {'scale_pivot': 'Body-only fresh GLB bounds are1.7400000095m/ground0; weapon pivot absent, full requirement remains failed.',
               'export-roundtrip': 'Actual fresh static GLB import preserves39746tri/3packedmaps/noexternalURI; required rig and animation absent, full check fails.',
               'deformation': 'Actual zero-bone baseline lacks deformation capability; no stress poses run, cannot pass.',
               'package_complete': 'Baseline .blend/.glb/README exist, full requested character+sword+rig+animation+effects package absent.'}
    checks[key] = {'status': 'fail', 'method': methods.get(key, 'Actual independent five-view review and source inventory: this full requirement is missing or defective; see review.'), 'artifacts': support}
evidence = {'schema_version': 1, 'request_id': ID, 'request_sha256': workbench.request_sha256(request), 'checks': checks,
            'subject_artifacts': content, 'deliverables': content+[artifact(f'assets/processed/{ID}/baseline/README.json')]}
ended = datetime.now(timezone.utc)
started = datetime.fromisoformat(start['baseline_started_utc'])
trial = {'id':'baseline', 'parent_id':None, 'status':'completed', 'started_utc':started.isoformat(), 'ended_utc':ended.isoformat(),
         'elapsed_seconds':(ended-started).total_seconds(), 'protocol_sha256':workbench.quality_sha256(request), 'reviewer':review['reviewer'],
         'previews':{v:artifact(f'runs/qa/{ID}/baseline/{v}.png') for v in request['quality']['protocol']['views']}, 'scores':review['scores'], 'evidence':evidence}
ledger = {'schema_version':1, 'request_id':ID, 'request_sha256':workbench.request_sha256(request), 'protocol_sha256':workbench.quality_sha256(request),
          'trials':[trial], 'previous_phase_preserved':request['phase_history'], 'clock_policy':start['time_accounting']}
result = workbench.compare_quality(request, ledger)
assert not result['blockers'], result
save(QA/'baseline/evidence.json', evidence)
save(QA/'quality-ledger.json', ledger)
save(QA/'comparison-baseline.json', result)
save(QA/'v001-start.json', {'id':'v001', 'parent_id':'baseline', 'started_utc':ended.isoformat(), 'before_candidate_work':True,
                          'hypothesis':'Retain neutral source UV/shape, diagnose local seams, segment clothing by visible seams, author joint and finger weights, then add independent sword/sequence/effects without replacing anatomy.',
                          'change':'One source-preserving local refinement; preflight three stress poses and early fresh GLB comparison before full animation.',
                          'old_trials_preserved':True})
print(json.dumps(result, ensure_ascii=False))
