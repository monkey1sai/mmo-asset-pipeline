"""Archive exact tested candidate source before restoring selected baseline code."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
run=json.loads((OUT/'20261007t101631z-p4-results.json').read_text())
destination=OUT/'candidate-01-source'
destination.mkdir(exist_ok=False)
rows=[]
for rel in ['src/p4.js','src/cv1-affine-fk.js','test/affine-fk.test.js']:
    source=ROOT/'tools/runtime-qa/three'/rel
    data=source.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if rel.startswith('src/'):
        assert digest==run['inputs']['harness'][rel]['sha256']
    target=destination/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:
        f.write(data)
    rows.append({'runtime_path':'tools/runtime-qa/three/'+rel,'archive_path':target.relative_to(ROOT).as_posix(),'sha256':digest,'bytes':len(data)})
(destination/'manifest.json').write_text(json.dumps({'candidate':'candidate-01-affine-foot-lock-fk','run':'20261007t101631z','disposition':'discard_not_adopted','source_files':rows},indent=1))
print('CANDIDATE_ARCHIVE_VERIFIED '+str(len(rows)))
