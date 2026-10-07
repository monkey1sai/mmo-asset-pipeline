"""Restore only named local P4 payloads; verify source and destination hashes."""
from pathlib import Path
import hashlib
import json
import shutil

SOURCE = Path(r'C:\Repos\mmo-asset-pipeline')
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

result_path = 'runs/qa/ro-swordsman-character-v1/v001/p4/runtime/20261007t054356z-p4-results.json'
old = json.loads((SOURCE / result_path).read_text())
records = [old['inputs'][key] for key in ('manifest', 'reference', 'reference_binary', 'rules', 'transitions')]
records += list(old['inputs']['glb'].values()) + list(old['inputs']['harness'].values())
transitions = json.loads((SOURCE / old['inputs']['transitions']['path']).read_text())
extra = [result_path, 'assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/ro_character_v001_b20-coatlie3.blend']
for clip in transitions['clips'].values():
    extra.extend([clip['blend'], clip['interaction']])
for rel in extra:
    p = SOURCE / rel
    records.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': sha(p)})
seen, evidence = set(), []
for record in records:
    rel = record['path']
    if rel in seen:
        continue
    seen.add(rel)
    source, destination = SOURCE / rel, ROOT / rel
    if SOURCE.resolve() not in source.resolve().parents or ROOT.resolve() not in destination.resolve().parents:
        raise SystemExit('PATH_OUTSIDE_ROOT')
    if source.stat().st_size != record['bytes'] or sha(source) != record['sha256']:
        raise SystemExit(f'SOURCE_HASH_MISMATCH {rel}')
    if not destination.exists() or sha(destination) != record['sha256']:
        if destination.exists() and not destination.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            raise SystemExit(f'REFUSE_OVERWRITE_NONPOINTER {rel}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    assert sha(destination) == record['sha256']
    evidence.append(record)
(OUT / 'input-hashes.json').write_text(json.dumps({'source_commit': 'c5ed6c8f2062692a0941a9fae3d6e06847e5c279', 'inputs': evidence}, indent=2) + '\n')
print(json.dumps({'verified_inputs': len(evidence), 'bytes': sum(x['bytes'] for x in evidence)}))
