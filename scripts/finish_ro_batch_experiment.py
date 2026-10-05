"""Archive batch-first actual result and prepare only evidence-based core fallback."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005'
OPERATION = 'ro-core-fallback-20261003-001'

def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

request = workbench.read_json(ROOT / 'requests/ro-swordsman-combo-r005.json')
phase = workbench.read_json(QA / 'phase-accounting.json')
start = workbench.read_json(QA / 'v001-start.json')
ledger = workbench.read_json(QA / 'quality-ledger.json')
if len(ledger['trials']) != 1 or ledger['trials'][0]['id'] != 'baseline':
    raise RuntimeError('Preserve already recorded trials')
ended = datetime.now(timezone.utc)
elapsed = (ended-datetime.fromisoformat(start['started_utc'])).total_seconds()
phase_elapsed = (ended-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()
if elapsed >= phase['budget']['trial_seconds'] or phase_elapsed >= phase['budget']['total_seconds']:
    raise RuntimeError('Original time budget exhausted; do not prepare next generation')
review = {'reviewer':'Independent batch_review; actual bind five views, three stress poses and grip closeups',
    'verdict':'NO_SHIP',
    'verified_progress':['One real batch generation consumed service-reported0.5 credits; six parts separated with geometry/UV/materials preserved.',
        '8-object assembly with mirrored armor uses55488tri.',
        'Gear-bone core contamination repaired; gross pants-to-sword spikes visibly removed.',
        '269 coincident seam groups with different weights diagnosed; position weld6651->5820 preserves UV loops; nonmanifold0.',
        '48 editable FK bones, normalized max4 influences; 3 real poses have reachable wrist targets.',
        'Fresh static GLB import preserves8meshes,48joints,55488tri and3embedded2k maps. No animation exists.'],
    'remaining_failures':['Face/eyes/brows/nose/mouth/hairline blurred in bind, source-quality defect.',
        'Palm/wrist collapse, hanging unposed thumb and hand overlap; zero bone residual does not prove grip.',
        'Shoulder/underarm cloth stretched; current bone/weight/topology cause not fully separated.',
        'Waist/hip and crouch pants/coat intersections.',
        'No full300frame sequence, separate skill effects or animated GLB roundtrip.'],
    'fallback':'Only core merits source-quality generation comparison now. Reuse armor/coat/sword; rig defects require separate local tests and are not proven source failures.',
    'source_regeneration_guarantees_animation':False}
save(QA / 'v001-final-review.json',review)
save(QA / 'quality-ledger-before-v001.json',ledger)
trial = {'id':'v001','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':ended.isoformat(),'elapsed_seconds':elapsed,'protocol_sha256':workbench.quality_sha256(request),
    'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
    'change':'Source-preserving affine assembly fit and covered-clothing tailoring; independent rigid equipment, native anatomy-only heat, UV-position seam weld and jointly reachable stress grip authoring. All intermediate methods and failures retained.',
    'failure_reason':'PRODUCT_FAILURE: real candidate remains NO_SHIP for face clarity, wrist/thumb grip, shoulder and garment deformation. TEST_FAILURE rig contamination/seam inconsistency and unreachable target diagnosed/repaired; full animation held by preflight. ENVIRONMENT_FAILURE preferences-reset extension cleanup recorded separately; no unsafe repair performed.',
    'supporting_reports':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in [QA/'v001-final-review.json',QA/'v001-rig-seams/preflight.json',QA/'v001-glb-roundtrip/roundtrip.json',QA/'roundtrip-environment-failure.json']]}
ledger['trials'].append(trial)
(QA / 'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
comparison = workbench.compare_quality(request,ledger)
save(QA / 'comparison-v001.json',comparison)
if comparison['blockers'] or comparison['best_trial_id'] != 'baseline':
    raise RuntimeError(comparison)
design = ROOT / 'assets/raw/ro-swordsman-combo/design-v005'
design.mkdir()
generated = Path(r'C:\Users\IOT\.codex\generated_images\01a0fc1d-f673-7ff3-bd4a-0dbfe6096075\exec-e75b1399-01db-4084-ada0-4d12513d6b99.png')
image = design / 'core-white.png'
with generated.open('rb') as source,image.open('xb') as destination:
    shutil.copyfileobj(source,destination)
save(design/'manifest.json',{'source':str(generated),'tool':'built-in image_gen',
    'input_reference':{'path':'assets/raw/ro-swordsman-combo/design-v003/core.png','sha256':sha(ROOT/'assets/raw/ro-swordsman-combo/design-v003/core.png')},
    'output':{'path':image.relative_to(ROOT).as_posix(),'sha256':sha(image),'bytes':image.stat().st_size},
    'edit':'Replace halo/background with white, preserve character design/pose. Source input revision only; frozen evaluation references and targets unchanged.',
    'visual_check':'One complete core, clear face and five open fingers on each hand; no equipment or text.',
    'pixel_edits_by_script':False,'geometry_acceptance':False})
spec = {'operation_id':OPERATION,'request':'requests/ro-swordsman-combo-r005.json',
    'images':[image.relative_to(ROOT).as_posix()], 'output_directory':'assets/raw/ro-swordsman-combo/rodin-v005/core',
    'parameters':{'tier':'Gen-2.5-High','mesh_mode':'Quad','quality_override':7000,'quad_normal':True,
        'geometry_file_format':'glb','material':'PBR','texture_mode':'high','texture_delight':True,
        'TAPose':True,'is_symmetric':'symmetric','image_label':['F'],'seed':4501,'preview_render':True},
    'authorization':{'spending_scope':'User already authorizes demand-driven existing monthly/regular credits and failure-only fallback. Exact new global state filename still requires authority; no topup/upgrade or commit/push.',
        'credit_pool':'existing_monthly_or_regular','no_topup_or_upgrade':True}}
save(QA/'api-spec-core-fallback.json',spec)
client = Client(ROOT)
if client.record_path(OPERATION).exists() or client.private_path(OPERATION).exists():
    raise RuntimeError('Reconcile existing fallback operation; never resubmit')
client.prepare(spec)
plan = client.plan(OPERATION)
save(QA/'core-fallback-prepared.json',{'operation_id':OPERATION,'state':'prepared_not_submitted',
    'global_state_file':str(client.private_path(OPERATION)),'global_write_authority':'pending_exact_filename',
    'plan_sha256':plan['plan_sha256'],'input_sha256':sha(image),'estimated_credits':plan['estimated_credits'],
    'reason':'Static source face detail failure; single core input comparison. No promise of automatic rig/animation repair.',
    'whole_character_triangle_budget':60000,'reused_equipment_triangles':43852,'maximum_replacement_core_triangles':16148,
    'quad_quality_override':7000,'generated_triangle_count_guaranteed':False,
    'remaining_assembly_revisions':2,'original_phase_started_utc':phase['baseline_started_utc'],'phase_clock_reset':False,
    'next_checks':['Inspect source face/material density/hands/shoulder topology before replacing old core.',
        'Check actual triangles; do not exceed whole character60000.',
        'Re-measure joints and separate rig errors from source comparison.',
        'Pass stress poses before300frame animation/effects and actual animated GLB roundtrip.'],
    'envelope':{'destination':['https://api.hyper3d.com/api/v2/rodin',str(client.private_path(OPERATION))],
        'purpose':'Evidence-based single core fallback comparison','allowed_operations':['one unique generation','same-task status/download','reserve/update only exact DPAPI file if authorized'],
        'data_transmitted':['one original character design image','validated nonsecret generation parameters'],
        'forbidden_operations':['old state overwrite','six-part automatic regeneration','secret output','topup/upgrade','stage/commit/push'],
        'stop_conditions':['missing exact global file authority','pending/unknown charge','file collision','input/provider drift','original phase budget exhausted']}})
print(json.dumps({'v001_verdict':'NO_SHIP','comparison':comparison,'fallback':OPERATION,'state_file':str(client.private_path(OPERATION)),'charged':False,'remaining_revisions':2},ensure_ascii=False))
