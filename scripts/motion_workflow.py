"""Request-bound, local-only bone-chain trajectory entry point.
No upload/API/runtime writes, source import, automatic acceptance or Git.
"""
import argparse
import json
from pathlib import Path
import identity
import art_sources
import workbench
from secondary_motion import ChainSolver
ROOT=Path(__file__).resolve().parents[1]


def simulate(request, profile, trajectory):
    errors=workbench.validate_request(request)
    if errors or request['task_type']!='rigged_character':raise ValueError('REQUEST_INVALID')
    solver=ChainSolver(profile);rows=[]
    last=None
    for sample in trajectory['samples']:
        time=sample['time_seconds']
        if type(time) not in (int,float) or not 0<=time<1e8 or (last is not None and time<last):raise ValueError('TIME_SEQUENCE')
        result=solver.advance(0 if last is None else time-last,sample['anchors'],paused=sample.get('paused',False),reset=sample.get('reset',False))
        rows.append({'time_seconds':time,**result});last=time
    if not rows:raise ValueError('TRAJECTORY_EMPTY')
    return {'schema_version':1,'request_id':request['id'],'request_sha256':identity.json_digest(request),
            'profile_sha256':identity.json_digest(profile),'trajectory_sha256':identity.json_digest(trajectory),
            'solver_constraints':'PASS' if all(r['constraints_status']=='PASS' for r in rows) else 'FAIL',
            'rows':rows,'motion_origin':'provided_local_trajectory_not_mixamo','game_ready':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('request','profile','trajectory','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args(argv)
    root=ROOT.resolve()
    result=simulate(*(identity.read_json(identity.command_path(root,getattr(a,k))) for k in ('request','profile','trajectory')))
    # Reuse receipt portable paths and no-reparse boundary for writable evidence.
    relative=identity.command_path(root,a.out).relative_to(root).as_posix();art_sources.safe_relative(relative)
    if not relative.startswith('runs/qa/'):raise ValueError('OUTPUT_SCOPE')
    path=art_sources.no_symlinks(root,relative);encoded=json.dumps(result,allow_nan=False,ensure_ascii=False,indent=2)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(encoded+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}));return 0 if result['solver_constraints']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
