"""Task-local snapshot and byte-preserving import; never edit the two source trees."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path('C:/Repos/mmo-asset-pipeline')
TARGET = ROOT / 'tmp/consolidate-20261007'
EVIDENCE = TARGET / 'runs/qa/consolidation-20261007'
SOURCES = {'root': ROOT, 'ro': ROOT / 'tmp/art-quality-loop'}
ROOT_ALLOWED = (
    'assets/processed/cl-barracks-set-v1/', 'assets/raw/cl-barracks-set-v1/',
    'deliveries/cl-barracks-set-v1/', 'runs/qa/cl-barracks-set-v1/',
)
ROOT_FILES = {'library/index.json', 'tests/test_workbench.py', 'requests/cl-barracks-set-v1.json',
              'runs/cl-barracks-set-v1-plan.json', 'tools/blender/build_box_assets.py',
              'tools/blender/render_preview.py', 'tools/glb_bounds.py'}
RO_ALLOWED = ('assets/processed/ro-swordsman-character-v1/', 'runs/qa/ro-swordsman-character-v1/',
              'runs/qa/git-portability-20261007/', 'runs/qa/git-portability-20261007-combo/')
RO_FILES = {'scripts/cv1_author_clip.py', 'scripts/cv1_p4_manifest.py', 'scripts/cv1_p4_scenarios.py',
            'scripts/cv1_fx_layer.py', 'docs/handoffs/codex-character-animation-v1-combo-20261007.md'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True).stdout


def capture(label, root):
    staged = git(root, 'diff', '--cached', '--name-only', '-z')
    if staged:
        raise ValueError(f'{label}: original index has staged work; preserve and stop')
    entries, excluded = [], []
    fields = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all').decode().split('\0')
    for field in fields:
        if not field:
            continue
        status, name = field[:2], field[3:]
        if status not in {' M', '??'}:
            raise ValueError(f'{label}: unexpected status {status} {name}')
        if label == 'root' and name.startswith('.claude/'):
            excluded.append({'path': name, 'reason': 'local preview configuration, not a portable deliverable'})
            continue
        allowed = (name in ROOT_FILES or name.startswith(ROOT_ALLOWED)) if label == 'root' else (name in RO_FILES or name.startswith(RO_ALLOWED))
        if not allowed:
            raise ValueError(f'{label}: path outside reviewed import scope: {name}')
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink():
            raise ValueError(f'{label}: unsafe source path: {name}')
        if any(part in {'.git', '.aws', '.codex'} or part.startswith('.env') for part in Path(name).parts):
            raise ValueError('credential/config area refused')
        entries.append({'source': label, 'path': name, 'status': status.strip(),
                        'bytes': path.stat().st_size, 'sha256': digest(path)})
    return {'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'index_sha256': hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest(),
            'files': sorted(entries, key=lambda item: item['path']), 'excluded': excluded}


def save(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def prepare():
    if git(TARGET, 'rev-parse', 'HEAD').decode().strip() != '08c454e6c6e7566f7a7625953773b6eb18693f5c':
        raise ValueError('unexpected integration base')
    if git(TARGET, 'status', '--porcelain=v1', '-z'):
        raise ValueError('integration tree is not empty')
    snapshots = {label: capture(label, root) for label, root in SOURCES.items()}
    base_index = json.loads((TARGET / 'library/index.json').read_text(encoding='utf-8-sig'))
    root_index = json.loads((ROOT / 'library/index.json').read_text(encoding='utf-8-sig'))
    old = {item['id']: item for item in base_index['entries']}
    new = {item['id']: item for item in root_index['entries']}
    if any(new.get(key) != value for key, value in old.items()):
        raise ValueError('root library would overwrite existing semantic entries')
    if set(new) - set(old) != {'cl-barracks-v1', 'cl-brazier-v1', 'cl-wreck-v1'}:
        raise ValueError('unexpected library additions')
    all_files = [item for snap in snapshots.values() for item in snap['files']]
    if len({item['path'] for item in all_files}) != len(all_files):
        raise ValueError('overlapping source deltas')
    for item in all_files:
        source = SOURCES[item['source']] / item['path']
        target = TARGET / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(target) != item['sha256']:
            raise ValueError(f'copy mismatch: {item["path"]}')
    if snapshots != {label: capture(label, root) for label, root in SOURCES.items()}:
        raise ValueError('source changed during import; stop')
    save('source-manifest.json', {'schema_version': 1, 'base': '08c454e6c6e7566f7a7625953773b6eb18693f5c',
                                'sources': snapshots, 'files': all_files,
                                'library_semantic_additions': sorted(set(new) - set(old)),
                                'note': 'Exact existing bytes imported. Raw timing markers and local runner are historical evidence, not live jobs or portable tools.'})
    print(json.dumps({'imported': len(all_files), 'bytes': sum(item['bytes'] for item in all_files),
                      'by_source': {label: len(snap['files']) for label, snap in snapshots.items()},
                      'source_stability': 'same before and after import'}))


def verify():
    manifest = json.loads((EVIDENCE / 'source-manifest.json').read_text(encoding='utf-8'))
    problems = [item['path'] for item in manifest['files'] if digest(TARGET / item['path']) != item['sha256']]
    problems += [f'source bytes changed: {item["source"]}:{item["path"]}' for item in manifest['files']
                 if digest(SOURCES[item['source']] / item['path']) != item['sha256']]
    update = EVIDENCE / 'source-state-update.json'
    expected_sources = json.loads(update.read_text(encoding='utf-8'))['observed_sources'] if update.exists() else manifest['sources']
    for label, expected in expected_sources.items():
        if capture(label, SOURCES[label]) != expected:
            problems.append(f'source changed: {label}')
    print(json.dumps({'files': len(manifest['files']), 'problems': problems}))
    if problems:
        raise ValueError('source/import bytes changed')


def reconcile():
    manifest = json.loads((EVIDENCE / 'source-manifest.json').read_text(encoding='utf-8'))
    observed = {label: capture(label, root) for label, root in SOURCES.items()}
    if observed['root']['head'] != '7423acdfda94d62ed455e8ed343da6bc024b6fce':
        raise ValueError('unexpected external source transition')
    if observed['ro'] != manifest['sources']['ro'] or observed['root']['files'] or observed['root']['excluded'] != manifest['sources']['root']['excluded']:
        raise ValueError('source change exceeds the independently committed barracks batch')
    committed = set(git(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', observed['root']['head']).decode().strip('\0').split('\0'))
    if committed != {v['path'] for v in manifest['sources']['root']['files']}:
        raise ValueError('external commit path set differs from the 37 snapshotted root files')
    mismatches = [f'{v["source"]}:{v["path"]}' for v in manifest['files'] if digest(SOURCES[v['source']] / v['path']) != v['sha256']]
    if mismatches:
        raise ValueError('external source content changed: ' + str(mismatches))
    save('source-state-update.json', {'reason': 'Root HEAD/index changed outside this writer during preparation. Existing root results were independently committed as 7423acd; all 411 original source file bytes still match. Original snapshot retained unchanged.',
                                     'observed_sources': observed, 'source_content_mismatches': mismatches,
                                     'root_committed_paths': sorted(committed),
                                     'plan': 'Preserve 7423acd as a merge parent after byte-preserving import commits; do not reset either original tree.'})
    print(json.dumps({'root_head': observed['root']['head'], 'root_committed_files': len(committed), 'source_bytes_mismatches': len(mismatches)}))


def scan():
    manifest = json.loads((EVIDENCE / 'source-manifest.json').read_text(encoding='utf-8'))
    source = TARGET / 'runs/qa/git-portability-20261007/precommit-check-used.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PATTERNS' for t in n.targets))
    patterns = {}
    for key, value in zip(assignment.value.keys, assignment.value.values):
        flags = re.I if len(value.args) > 1 else 0
        patterns[ast.literal_eval(key)] = re.compile(ast.literal_eval(value.args[0]).encode('ascii'), flags)
    hits = []
    for item in manifest['files']:
        with (TARGET / item['path']).open('rb') as handle:
            offset, tail = 0, b''
            while chunk := handle.read(1024 * 1024):
                body = tail + chunk
                for label, pattern in patterns.items():
                    for match in pattern.finditer(body):
                        hits.append({'path': item['path'], 'offset': offset - len(tail) + match.start(), 'pattern': label})
                offset += len(chunk)
                tail = body[-4096:]
    report = {'files': len(manifest['files']), 'bytes': sum(item['bytes'] for item in manifest['files']),
              'hits': hits, 'scope': 'All imported raw bytes, including large/LFS/binary files; pattern matches only. Compressed metadata and visual privacy need separate review.'}
    save('raw-byte-pattern-scan.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify, 'scan': scan, 'reconcile': reconcile}[sys.argv[1]]()
