"""Single artist-selected bone-only grasp candidate; no free contact search."""
from pathlib import Path
from datetime import datetime,timezone
import sys,bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import contacts
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';read,save,artifact=common.read,common.save,common.artifact
start=read(QA/'v001-start.json');contract=read(QA/'local-contract.json');folder=QA/'v001-authored-controls';folder.mkdir()
out=ROOT/'assets/processed/ro-swordsman-combo-r010/v001-authored-controls';out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
rest=common.geometry(ob);ww=common.weights(ob)
grip.controls(rig,start['controls'],start['splays'],splay_first=True)
self_report,pts=grip.capture(ob,rig,rest,'authored-controls',start['controls'],ww)
contact=contacts(ob,sword,rig,contract['pads'],'authored-controls',{'controls':start['controls'],'splays':start['splays']})
gate=not self_report['transverse_pairs'] and not self_report['degenerate_triangles'] and contact['surface_gate_pass'] and self_report['minimum_edge_ratio']>=.25 and self_report['maximum_edge_stretch']<=3
ob.data.materials.clear();ob.data.materials.append(common.material('r010AuthoredGray',(.55,.55,.55)))
dest=out/'right_hand_authored_controls.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
common.render(folder,'authored')
save(folder/'posed-points.json',{'points':[list(p) for p in pts]})
assert common.geometry(ob)==rest and common.weights(ob)==ww
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'artifact':artifact(dest),'source':start['source'],'self':self_report,'contact':contact,
 'controls':start['controls'],'splays':start['splays'],'weapon_shift':start['weapon_shift'],'bone_only':True,'geometry_UV_weights_unchanged':True,'numeric_gate':gate,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))],'raw_points':artifact(folder/'posed-points.json'),'new_credits':0})
print('R010_V001 '+str({'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'numeric_gate':gate}))
