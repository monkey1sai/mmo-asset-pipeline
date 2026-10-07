"""All 118 fixed reference poses, pre-IK FK only; unchanged Blender evaluator."""
from pathlib import Path
import json
import runpy
import sys
import bpy
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.argv = ['blender','--','--scenarios','runs/qa/ro-swordsman-character-v1/v001/p4/transitions-05.json',
 '--registry','runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json',
 '--rules','assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/corrective-rules.json',
 '--contract','runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json',
 '--fixtures','assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/contact-fixtures.json',
 '--out',str(OUT/'fk-init'),'--continuity-only','--only','__diagnostic_no_scenario__']
ns = runpy.run_path(str(ROOT/'scripts/cv1_transition_check.py'))
refs = json.loads((ROOT/'runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/transition-reference.json').read_text())
rows = []
for block in refs['blocks']:
    scenario = next(s for s in ns['spec']['scenarios'] if s['id'] == block['scenario'])
    pose,_,_ = ns['blended_pose'](scenario, block['t'])
    ns['set_pose'](pose)
    rows.append({'label':block['label'], 'joints': {f'{n}.{s}': ns['world_point'](ns['arm'].pose.bones[f'{n}.{s}'].head)
                for s in ['L','R'] for n in ['upper_leg','lower_leg','foot','toe']}, 'soles':ns['sole_points']()})
(OUT/'blender-fk.json').write_text(json.dumps({'scope':'diagnostic_only_pre_ik','blender':bpy.app.version_string,'script_sha256':ns['SCRIPT_SHA256'],'rows':rows},indent=1))
print('FK_DIAGNOSTIC_SAVED '+str(len(rows)))
