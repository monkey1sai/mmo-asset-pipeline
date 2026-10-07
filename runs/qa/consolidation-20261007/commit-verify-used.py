"""Verify all 411 imported files against immutable Git blobs and local LFS objects."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def git(*args, data=None):
    return subprocess.run(['git', '-C', str(ROOT), *args], input=data, capture_output=True, check=True).stdout


manifest = json.loads((OUT / 'source-manifest.json').read_text(encoding='utf-8'))
head = git('rev-parse', 'HEAD').decode().strip()
common = Path(git('rev-parse', '--git-common-dir').decode().strip())
if not common.is_absolute():
    common = (ROOT / common).resolve()
attrs = {}
names = [item['path'] for item in manifest['files']]
raw = git('check-attr', 'text', 'eol', 'filter', '--stdin', '-z', data='\0'.join(names).encode()).decode().split('\0')
for i in range(0, len(raw) - 2, 3):
    attrs.setdefault(raw[i], {})[raw[i+1]] = raw[i+2]
problems = []
regular = lfs = lfs_bytes = 0
for item in manifest['files']:
    path = item['path']
    blob = git('show', head + ':' + path)
    if attrs[path]['filter'] == 'lfs':
        lfs += 1
        fields = dict(line.split(' ', 1) for line in blob.decode().splitlines() if ' ' in line)
        oid = fields.get('oid', '').removeprefix('sha256:')
        obj = common / 'lfs/objects' / oid[:2] / oid[2:4] / oid
        if oid != item['sha256'] or fields.get('size') != str(item['bytes']) or not obj.is_file():
            problems.append('pointer/local object: ' + path)
        elif hashlib.sha256(obj.read_bytes()).hexdigest() != item['sha256']:
            problems.append('LFS object hash: ' + path)
        lfs_bytes += item['bytes']
    else:
        regular += 1
        if len(blob) != item['bytes'] or hashlib.sha256(blob).hexdigest() != item['sha256']:
            problems.append('Git blob bytes: ' + path)
        if attrs[path]['text'] != 'unset' and attrs[path]['eol'] != 'lf':
            problems.append('checkout bytes not protected from autocrlf: ' + path)
result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'payload_head': head,
          'parents': git('show', '-s', '--format=%P', head).decode().strip().split(),
          'git_tree': git('rev-parse', head + '^{tree}').decode().strip(),
          'files': len(names), 'ordinary_git_blobs': regular, 'lfs_paths': lfs, 'lfs_bytes': lfs_bytes,
          'problems': problems, 'scope': 'Immutable commit bytes and local LFS objects only. No remote publication or restore claim.'}
(OUT / 'commit-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(1 if problems else 0)
