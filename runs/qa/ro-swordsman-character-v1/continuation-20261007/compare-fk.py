from pathlib import Path
import json
import math
OUT=Path(__file__).resolve().parent
b=json.loads((OUT/'blender-fk.json').read_text())
r=json.loads((OUT/'runtime-fk.json').read_text())
convert=lambda a: [a[0],-a[2],a[1]]
rows=[]
for bb,rr in zip(b['rows'],r['rows']):
    assert bb['label']==rr['label']
    errors={}
    for category,affine in [('joints','affineJoints'),('soles','affineSoles')]:
        for key,target in bb[category].items():
            errors[f'{category}/{key}']={'trs_um':math.dist(target,convert(rr[category][key]))*1e6,
                                        'affine_um':math.dist(target,convert(rr[affine][key]))*1e6}
    rows.append({'label':bb['label'],'errors':errors})
flat=[v for row in rows for v in row['errors'].values()]
summary={'samples':len(rows),'points':len(flat),'trs_max_um':max(x['trs_um'] for x in flat),
         'affine_max_um':max(x['affine_um'] for x in flat),
         'trs_rms_um':math.sqrt(sum(x['trs_um']**2 for x in flat)/len(flat)),
         'affine_rms_um':math.sqrt(sum(x['affine_um']**2 for x in flat)/len(flat)),
         'improved_points':sum(x['affine_um']<x['trs_um'] for x in flat),
         'worsened_over_1um':sum(x['affine_um']-x['trs_um']>1 for x in flat)}
(OUT/'fk-comparison.json').write_text(json.dumps({'scope':'diagnostic_only_not_runtime_candidate','summary':summary,'rows':rows},indent=1))
print(json.dumps(summary))
for row in rows:
    if 'combo-idle-end' in row['label']:
        print(json.dumps(row))
