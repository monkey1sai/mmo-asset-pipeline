"""Task-local sparse restore plan and byte verification, no transport mutations."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

SOURCE = Path('C:/Repos/mmo-asset-pipeline/tmp/consolidate-20261007')
TOOLS = Path(__file__).resolve().parent
CLONE = Path('C:/Repos/mmo-asset-pipeline/tmp/main-restore-20261007')
FIXED = '1ae4f330b2f30ba863785801634e4a803de04b5c'
ORIGIN = 'git@github.com:monkey1sai/mmo-asset-pipeline.git'
LFS = CLONE / '.git/lfs'
HOOKS = TOOLS / 'no-filter-hooks'


def git(root, *args, data=None, env=None):
    result = subprocess.run(['git', '-c', 'core.hooksPath=' + str(HOOKS), '-c', 'lfs.storage=' + str(LFS), '-C', str(root), *args],
                            input=data, capture_output=True, env=env)
    if result.returncode:
        error = re.sub(rb'https?://\S+', b'[HTTP URL redacted]', result.stderr)
        print(error.decode('utf-8', 'replace')[:2000])
        raise SystemExit(result.returncode)
    return result.stdout


def hooks_empty():
    if list(HOOKS.iterdir()):
        raise ValueError('new no-filter hook directory is not empty; stop')


def save(name, value):
    (TOOLS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def plan():
    manifest = json.loads((SOURCE / 'runs/qa/consolidation-20261007/source-manifest.json').read_text(encoding='utf-8'))
    names = [v['path'] for v in manifest['files']]
    extras = ['.gitattributes'] + [p.relative_to(SOURCE).as_posix() for p in (SOURCE / 'runs/qa/consolidation-20261007').rglob('*') if p.is_file()]
    paths = sorted(set(names + extras))
    for name in paths:
        if not re.fullmatch(r'[A-Za-z0-9._/-]+', name) or '..' in Path(name).parts or name.startswith('/'):
            raise ValueError('unsafe or glob-sensitive sparse pattern')
    attrs = git(SOURCE, 'check-attr', 'filter', '--stdin', '-z', data='\0'.join(names).encode()).decode().split('\0')
    lfs = sorted(attrs[i] for i in range(0, len(attrs)-2, 3) if attrs[i+2] == 'lfs')
    if len(lfs) != 70:
        raise ValueError('unexpected LFS path count')
    (TOOLS / 'restore-paths.txt').write_text('\n'.join('/'+p for p in paths)+'\n', encoding='utf-8', newline='\n')
    (TOOLS / 'restore-lfs-include.txt').write_text(','.join(lfs), encoding='utf-8', newline='\n')
    extra_refs = [{'path': p, 'bytes': (SOURCE/p).stat().st_size, 'sha256': hashlib.sha256((SOURCE/p).read_bytes()).hexdigest()} for p in extras]
    save('restore-plan.json', {'fixed_head': FIXED, 'origin': ORIGIN, 'clone': str(CLONE), 'lfs_storage': str(LFS),
                               'source_files': manifest['files'], 'extra_refs': extra_refs, 'lfs_paths': lfs,
                               'sparse_files': len(paths), 'scope': 'Current 411-file batch and consolidation receipts only.',
                               'method': 'No-checkout GitHub partial clone; raw Git blobs; a local-only 70-pointer scan commit for explicit LFS fetch. No filters or working-tree checkout. No filter.required override.'})
    print(json.dumps({'sparse_files': len(paths), 'lfs_paths': len(lfs), 'source_files': len(names)}))


def preflight():
    hooks_empty()
    head = git(CLONE, 'rev-parse', 'HEAD').decode().strip()
    origin = git(CLONE, 'remote', 'get-url', 'origin').decode().strip()
    alternate = CLONE / '.git/objects/info/alternates'
    lines = git(CLONE, 'lfs', 'env').decode().splitlines()
    media = next((line.split('=',1)[1] for line in lines if line.startswith('LocalMediaDir=')), None)
    endpoint = next((line[len('Endpoint='):].split(' (auth=',1)[0] for line in lines if line.startswith('Endpoint=')), None)
    endpoint_ok = endpoint == 'https://github.com/monkey1sai/mmo-asset-pipeline.git/info/lfs'
    references = next((line.split('=',1)[1] for line in lines if line.startswith('LocalReferenceDirs=')), '')
    obj_files = list((LFS/'objects').rglob('*')) if (LFS/'objects').exists() else []
    count = sum(p.is_file() for p in obj_files)
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'head': head,
              'head_matches': head == FIXED, 'origin_matches': origin == ORIGIN,
              'local_git_alternates_present': alternate.exists(), 'lfs_endpoint_is_expected_github_repo': endpoint_ok,
              'lfs_media_is_task_local': media is not None and Path(media).resolve() == (LFS/'objects').resolve(),
              'lfs_reference_dirs_empty': not references, 'lfs_files_before_pull': count}
    save('restore-preflight.json', report)
    print(json.dumps(report))
    if not all([report['head_matches'], report['origin_matches'], not alternate.exists(), endpoint_ok,
                report['lfs_media_is_task_local'], not references, count == 0]):
        raise SystemExit(1)
    hooks_empty()


def materialize():
    import os
    hooks_empty()
    plan = json.loads((TOOLS/'restore-plan.json').read_text(encoding='utf-8'))
    selected = {v['path']: v for v in plan['source_files'] + plan['extra_refs']}
    tree = {}
    for field in git(CLONE, 'ls-tree', '-r', '-z', FIXED).decode().split('\0'):
        if field:
            meta, name = field.split('\t', 1)
            mode, kind, oid = meta.split()
            if name in selected:
                if kind != 'blob' or mode not in {'100644', '100755'}:
                    raise ValueError('unexpected selected Git entry')
                tree[name] = (mode, oid)
    if set(tree) != set(selected):
        raise ValueError('selected path missing from immutable commit tree')
    # Follow Git v2.42 promisor-remote.c fetch_objects, preserving the clone
    # and any objects received by the initial incomplete-graph negotiation.
    missing = {line[1:].split()[0] for line in git(CLONE, 'rev-list', '--objects', '--missing=print', FIXED).decode().splitlines() if line.startswith('?')}
    needed = sorted({oid for _, oid in tree.values()} & missing)
    save('restore-git-transfer.json', {'initial_bulk_fetch_exit': 1,
                                     'initial_error': 'bad revision during ordinary fetch negotiation; did not send all necessary objects',
                                     'selected_git_blob_oids': len({oid for _, oid in tree.values()}), 'still_missing': len(needed),
                                     'new_evidence': 'Git v2.42 promisor-remote.c fetch_objects uses fetch.negotiationAlgorithm=noop and explicit --filter=blob:none.',
                                     'source': 'https://raw.githubusercontent.com/git/git/v2.42.0/promisor-remote.c',
                                     'retry_budget': 'One narrow corrective transfer for the missing subset only; no pack cleanup or all-history fetch.'})
    if needed:
        git(CLONE, '-c', 'fetch.negotiationAlgorithm=noop', 'fetch', 'origin', '--no-tags', '--no-write-fetch-head',
            '--recurse-submodules=no', '--filter=blob:none', '--stdin', data=('\n'.join(needed)+'\n').encode())
    command = ['git', '-c', 'core.hooksPath='+str(HOOKS), '-C', str(CLONE), 'cat-file', '--batch']
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pointer_entries = []
    for name, item in selected.items():
        mode, oid = tree[name]
        process.stdin.write((oid+'\n').encode()); process.stdin.flush()
        header = process.stdout.readline().decode().strip().split()
        if len(header) != 3 or header[:2] != [oid, 'blob']:
            raise ValueError('unexpected cat-file header')
        size = int(header[2])
        data = process.stdout.read(size)
        if len(data) != size or process.stdout.read(1) != b'\n':
            raise ValueError('incomplete cat-file blob')
        if name in plan['lfs_paths']:
            fields = dict(line.split(' ', 1) for line in data.decode().splitlines() if ' ' in line)
            if fields.get('oid') != 'sha256:'+item['sha256'] or fields.get('size') != str(item['bytes']):
                raise ValueError('LFS pointer differs from source manifest')
            pointer_entries.append((mode, oid, name))
        elif size != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('ordinary Git blob differs from manifest')
        target = CLONE/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    process.stdin.close()
    if process.wait() != 0:
        raise ValueError('cat-file failed')
    # The scanner uses ls-tree -l. A separate local-only thin commit avoids
    # fetching unrelated large Git blobs from a partial clone. HEAD stays FIXED.
    env = os.environ.copy()
    env['GIT_INDEX_FILE'] = str(TOOLS/'restore-lfs.index')
    if Path(env['GIT_INDEX_FILE']).exists():
        raise ValueError('temporary scan index already exists')
    index_data = ''.join(f'{mode} {oid}\t{name}\0' for mode, oid, name in pointer_entries).encode()
    git(CLONE, 'update-index', '-z', '--index-info', data=index_data, env=env)
    scan_tree = git(CLONE, 'write-tree', env=env).decode().strip()
    scan_commit = git(CLONE, 'commit-tree', scan_tree, '-m', 'chore(qa): 限定本批 LFS 還原掃描', env=env).decode().strip()
    save('restore-scan.json', {'original_remote_commit': FIXED, 'local_only_scan_commit': scan_commit,
                             'scan_tree': scan_tree, 'pointer_paths': len(pointer_entries),
                             'pointer_blobs': [{'path': name, 'blob': oid} for _, oid, name in pointer_entries],
                             'note': 'Local-only scanner input contains exact original GitHub pointer blobs. No branch, remote or HEAD change. It is not an alternate source commit or acceptance evidence.'})
    (TOOLS/'restore-scan-sha.txt').write_text(scan_commit, encoding='utf-8')
    if git(CLONE, 'rev-parse', 'HEAD').decode().strip() != FIXED:
        raise ValueError('HEAD changed')
    hooks_empty()
    print(json.dumps({'raw_git_files': len(selected), 'pointer_paths': len(pointer_entries), 'local_only_scan_commit': scan_commit}))


def restore_lfs():
    hooks_empty()
    plan = json.loads((TOOLS/'restore-plan.json').read_text(encoding='utf-8'))
    refs = {v['path']: v for v in plan['source_files']}
    for name in plan['lfs_paths']:
        item = refs[name]
        oid = item['sha256']
        obj = LFS/'objects'/oid[:2]/oid[2:4]/oid
        if not obj.is_file() or obj.stat().st_size != item['bytes'] or hashlib.sha256(obj.read_bytes()).hexdigest() != oid:
            raise ValueError('downloaded LFS object differs: '+name)
        shutil.copyfile(obj, CLONE/name)
    hooks_empty()
    print(json.dumps({'restored_lfs_paths': len(plan['lfs_paths']), 'hooks_empty': True}))


def verify():
    hooks_empty()
    plan = json.loads((TOOLS/'restore-plan.json').read_text(encoding='utf-8'))
    problems = []
    for item in plan['source_files'] + plan['extra_refs']:
        file = CLONE / item['path']
        if not file.is_file() or file.is_symlink():
            problems.append({'path': item['path'], 'reason': 'missing or symlink'})
        elif file.stat().st_size != item['bytes'] or hashlib.sha256(file.read_bytes()).hexdigest() != item['sha256']:
            problems.append({'path': item['path'], 'reason': 'bytes/hash mismatch'})
    head = git(CLONE, 'rev-parse', 'HEAD').decode().strip()
    if head != FIXED:
        problems.append({'reason': 'wrong checkout SHA'})
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'head': head,
              'source_files': len(plan['source_files']), 'ordinary_git_files': len(plan['source_files'])-len(plan['lfs_paths']),
              'lfs_paths': len(plan['lfs_paths']), 'extra_receipts_and_attributes': len(plan['extra_refs']),
              'problems': problems, 'scope': plan['scope'], 'storage': str(LFS),
              'source': 'Separate GitHub no-checkout partial clone, raw original Git blobs, and explicit LFS fetch using an exact-pointer local-only scan commit with empty task-local storage; no local alternates, filters, or checkout.'}
    save('restore-verification.json', report)
    print(json.dumps(report))
    raise SystemExit(1 if problems else 0)


if __name__ == '__main__':
    {'plan': plan, 'preflight': preflight, 'materialize': materialize, 'restore-lfs': restore_lfs, 'verify': verify}[sys.argv[1]]()
