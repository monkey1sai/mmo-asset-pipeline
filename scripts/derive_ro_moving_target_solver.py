"""Create a recorded narrow v003 derivation; preserve the faulty v002 source."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'runs/qa/ro-swordsman-combo-r009'
old=ROOT/'scripts/solve_ro_coupled_hand_contact.py'
new=ROOT/'scripts/solve_ro_moving_target_contact.py'
assert not new.exists()
source=old.read_text(encoding='utf-8')
before="    residual=np.array([component for i,target in zip(ids or chosen, targets or target_positions) for component in pts[i]-target])"
after="""    moving_targets = [target + Vector(shift) - guide_shift for target in targets] if targets is not None else target_positions
    residual=np.array([component for i,target in zip(ids or chosen, moving_targets) for component in pts[i]-target])"""
assert source.count(before)==1
source=source.replace(before,after).replace("QA/'v002-start.json'","QA/'v003-start.json'").replace("'v002-coupled-IK'","'v003-moving-target'").replace('ro-swordsman-combo-r009/v002-coupled-IK','ro-swordsman-combo-r009/v003-moving-target').replace("right_hand_coupled_contact.blend","right_hand_moving_target_contact.blend").replace('R009_COUPLED','R009_MOVING_TARGET')
before="    columns=[]"
after="    guide_shift=Vector([float(p[names.index('shift:'+str(i))]) for i in range(3)])\n    columns=[]"
assert source.count(before)==1;source=source.replace(before,after)
before="    J=np.stack(columns,axis=1);delta=-np.linalg.solve"
after="""    J=np.stack(columns,axis=1)
    for axis in range(3):
        column=J[:,names.index('shift:'+str(axis))].reshape(-1,3)
        expected=np.zeros_like(column);expected[:,axis]=-.03
        assert np.max(np.abs(column-expected))<1e-5, 'WEAPON_TRANSLATION_JACOBIAN_INCORRECT'
    delta=-np.linalg.solve"""
assert source.count(before)==1;source=source.replace(before,after)
with new.open('x',encoding='utf-8') as f:f.write(source)
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with (QA/'v003-solver-derivation.json').open('x',encoding='utf-8') as f:
    json.dump({'original':artifact(old),'derived':artifact(new),'purpose':'Fix only missing rigidtarget shift in derivative; explicitlycheck each translationJacobiancolumn. Originalfaultycode and83probev002 kept.',
               'different_candidate_counted':True,'no_old_retry_released':True},f,indent=2);f.write('\n')
print(json.dumps({'derived':str(new),'v002_source_preserved':True}))
