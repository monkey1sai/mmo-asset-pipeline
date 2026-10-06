"""Map existing actual weapon into the fixed source hand space, unchanged."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
from ro_hand_gate import evaluated,sword_solid
clock=read(QA/'phase-start.json');folder=QA/'weapon-probe';assert not folder.exists();folder.mkdir()
probe=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v001-source-preparation/joint-and-pole-probe.json')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/clock['baseline_source']['path']),load_ui=False,use_scripts=False)
fullrig=bpy.data.objects['ARM_RO_Swordsman'];fullrig.animation_data_clear();reset(fullrig)
for ob in bpy.context.scene.objects:
    if ob.type=='MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
        for key in list(ob.data.shape_keys.key_blocks)[1:]:key.value=0
bpy.context.view_layer.update()
state=json.loads(fullrig['state_json']);hf=state['hand_frames']['R']
width,front,down=[Vector(hf[n]) for n in ['width','front','down']]
R=Matrix((-width,-front,down)).transposed().to_4x4();wrist=fullrig.matrix_world@fullrig.data.bones['hand.R'].head_local
R.translation=wrist-R.to_3x3()@Vector(probe['wrist_center_scaled']);inverse=R.inverted()
sword=bpy.data.objects['SM_RO_sword'];p,t,_=sword_solid(sword)
local=[list(inverse@v) for v in p];bone=fullrig.pose.bones['sword']
head=inverse@fullrig.matrix_world@bone.head;tail=inverse@fullrig.matrix_world@bone.tail
save(folder/'actual-weapon.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'whole_source':clock['baseline_source'],
 'vertices':local,'triangles':[list(r) for r in t],'bone':{'head':list(head),'tail':list(tail)},
 'source_to_character_matrix':[list(r) for r in R],'determinant':R.to_3x3().determinant(),
 'actual_sword_closed_after_rest_weld':True,'sword_geometry_size_unchanged':True,
 'fit_scope':'Exact existingwrist andhandframe; weaponplacement measured, no newgeometry or positionoptimization.',
 'handle_interval_m':[-.112,.085]})
result=read(QA/'v002-direction/result.json')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];ob.data.materials.clear();ob.data.materials.append(material('r008WeaponProbeGray',(.55,.55,.55)))
me=bpy.data.meshes.new('MeasuredExistingSword');me.from_pydata(local,[],t);me.update();weapon=bpy.data.objects.new('MeasuredExistingSword',me);bpy.context.scene.collection.objects.link(weapon);weapon.data.materials.append(material('MeasuredSwordGray',(.18,.23,.28),metal=.6))
render(folder,'neutral-weapon')
print('R008_WEAPON '+json.dumps({'head':list(head),'tail':list(tail),'vertices':len(local),'triangles':len(t),'det':R.to_3x3().determinant()}))
