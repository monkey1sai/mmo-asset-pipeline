"""Nonmutating Blender exporter RNA capability readback for r010."""
from pathlib import Path
import json,bpy
root=Path(__file__).resolve().parents[1];qa=root/'runs/qa/ro-swordsman-combo-r010'
props=bpy.ops.export_scene.gltf.get_rna_type().properties
names=['export_animation_mode','export_force_sampling','export_frame_range','export_frame_step','export_attributes','export_morph','export_morph_animation','export_skins']
result={n:{'type':props[n].type,'enum':[i.identifier for i in props[n].enum_items] if props[n].type=='ENUM' else None} for n in names}
with (qa/'gltf-runtime-capabilities.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
