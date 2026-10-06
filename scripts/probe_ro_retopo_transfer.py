"""Read-only layer/material and source-guided hand transfer diagnosis."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'runs/qa/ro-swordsman-combo-r005/v003-hand-prototype/transfer-diagnostic.json'
if OUT.exists(): raise RuntimeError('Preserve transfer diagnosis')
result=[]
for relative in ['assets/processed/ro-swordsman-combo-r005/v002-digit-weights/ro_digit_weights.blend','assets/processed/ro-swordsman-combo-r005/v003-hand-prototype/ro_hand_prototype.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/relative),load_ui=False,use_scripts=False)
    core=bpy.data.objects['SM_RO_core']; slots={}
    for f in core.data.polygons:
        if all(core.data.vertices[i].co.x<-.34 and core.data.vertices[i].co.z<.923 for i in f.vertices): slots[f.material_index]=slots.get(f.material_index,0)+1
    result.append({'source':relative,'uv_layers':[{'name':u.name,'active':u.active,'active_render':u.active_render} for u in core.data.uv_layers],
        'materials':[m.name if m else None for m in core.data.materials],'hand_faces_material_counts':slots})
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result))
