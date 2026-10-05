"""Diagnose cuff topology and axial/radial sections before changing equipment."""
import json
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-fit/bracer-cavity-probe.json'
if OUT.exists(): raise RuntimeError('Preserve cavity diagnosis')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r005/v002-contact-calibrated/ro_contact_calibrated.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; result={}
for side in ['R','L']:
    ob=bpy.data.objects['SM_RO_bracer.'+side]; bone=rig.data.bones['lower_arm.'+side]
    center=bone.head_local.lerp(bone.tail_local,.5); axis=(bone.tail_local-bone.head_local).normalized()
    bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    chi=len(bm.verts)-len(bm.edges)+len(bm.faces)
    rows=[]
    for t in [-.10,-.06,0,.06,.10]:
        radii=[]; skin=[]
        for v in ob.data.vertices:
            d=v.co-center; z=d.dot(axis)
            if abs(z-t)<.009: radii.append((d-axis*z).length)
        for v in core.data.vertices:
            d=v.co-center; z=d.dot(axis)
            radius=(d-axis*z).length
            if abs(z-t)<.009 and radius<.13: skin.append(radius)
        rows.append({'axial':t,'gear_radius_min_max':[min(radii),max(radii)] if radii else None,'skin_radius_min_max':[min(skin),max(skin)] if skin else None})
    result[side]={'euler_characteristic_welded':chi,'nonmanifold':sum(not e.is_manifold for e in bm.edges),'sections':rows,'interpretation':'Euler characteristic alone is diagnostic; inspect cavity and sections, do not assert wearable.'}
    bm.free()
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
