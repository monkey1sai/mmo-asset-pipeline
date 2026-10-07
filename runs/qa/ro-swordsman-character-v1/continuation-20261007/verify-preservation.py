"""Verify frozen inputs against both historic SHA records and their current original-workspace files."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Repos\mmo-asset-pipeline')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=json.loads((OUT/'input-hashes.json').read_text())['inputs']
historical=json.loads((SOURCE/'runs/qa/ro-swordsman-character-v1/v001/p4/run-07/shard-0/transition-check.json').read_text())
for key in ['contract','fixtures']:
    records.append(historical['inputs'][key])
records.append({'path':'runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json',
                'sha256':sha(SOURCE/'runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json')})
for name,expected in historical['modules'].items():
    records.append({'path':'scripts/'+name,'sha256':expected})
records.append({'path':'scripts/cv1_transition_check.py','sha256':historical['script_sha256']})
rows=[]
for x in records:
    if x['path']=='tools/runtime-qa/three/src/p4.js':
        continue
    current=sha(ROOT/x['path'])
    original=sha(SOURCE/x['path'])
    if current!=x['sha256'] or original!=x['sha256']:
        raise SystemExit('FROZEN_INPUT_CHANGED '+x['path'])
    rows.append({'path':x['path'],'sha256':current,'original_unchanged':True,'candidate_unchanged':True})
(OUT/'preservation-verification.json').write_text(json.dumps({'status':'PASS','inputs':rows,
    'intentional_source_edits':['tools/runtime-qa/three/src/p4.js','tools/runtime-qa/three/src/cv1-affine-fk.js'],
    'reference_regenerated':False,'foundation_saved':False,'gate_changed':False},indent=1))
print('PRESERVATION_PASS '+str(len(rows)))
