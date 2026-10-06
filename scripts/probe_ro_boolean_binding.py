"""Read-only rigid gear weight audit after Boolean/decimate, v007."""
from pathlib import Path
import json
import bpy
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'; out=QA/'boolean-binding-diagnosis.json'; assert not out.exists()
rows=[]
for version,path in [('before','assets/processed/ro-swordsman-combo-r006/v006-wrist-loft-attempt2/ro_wrist_loft.blend'),('after','assets/processed/ro-swordsman-combo-r006/v007-underlay/ro_underlay_fit.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/path),load_ui=False,use_scripts=False)
    objects=[]
    for n in ['SM_RO_bracer.R','SM_RO_pauldron.R','SM_RO_pauldron.L']:
        ob=bpy.data.objects[n]; unweighted=[]; sums=[]; branch={}; influences={}; mixed=[]
        for v in ob.data.vertices:
            gs={ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}; total=sum(gs.values()); sums.append(total)
            if abs(total-1)>1e-5: unweighted.append({'id':v.index,'sum':total,'weights':gs,'position':list(v.co)})
            if len(gs)>1: mixed.append(v.index)
            for name,w in gs.items(): branch[name]=branch.get(name,0)+1
            influences[len(gs)]=influences.get(len(gs),0)+1
        objects.append({'object':n,'vertices':len(ob.data.vertices),'invalid_weights':unweighted,'mixed_ids':mixed,'branch_counts':branch,
                        'influence_counts':influences,'weight_sum_range':[min(sums),max(sums)],'modifiers':[(m.name,m.type) for m in ob.modifiers]})
    rows.append({'version':version,'objects':objects})
out.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'version':r['version'],'objects':[{'name':ob['object'],'vertices':ob['vertices'],'invalid_weights':len(ob['invalid_weights']),'mixed':len(ob['mixed_ids']),'branches':ob['branch_counts'],'influence_counts':ob['influence_counts']} for ob in r['objects']]} for r in rows]))
