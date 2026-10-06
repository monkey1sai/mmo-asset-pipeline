"""Measure and display original centers; no inferred automatic anatomy PASS."""
from pathlib import Path
from datetime import datetime,timezone
import sys,bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
from ro_hand_gate import evaluated
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
clock=read(QA/'phase-start.json');folder=QA/'baseline'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/clock['local_source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];common.reset(rig)
assert all(abs(rig.matrix_world[i][j]-(1 if i==j else 0))<1e-8 for i in range(4) for j in range(4))
assert all(abs(ob.matrix_world[i][j]-(1 if i==j else 0))<1e-8 for i in range(4) for j in range(4))
bpy.data.objects['SM_RO_LocalActualSword'].hide_render=True
ob.data.materials.clear();ob.data.materials.append(common.material('r009CenterGray',(.55,.55,.55)))
pts,tris,_=evaluated(ob);tree=BVHTree.FromPolygons(pts,tris,all_triangles=True)
rows=[];lines=[]
for n in ['finger1','finger2','finger3','finger4','thumb']:
    for j in range(1,4):
        bone=rig.data.bones[f'{n}_{j:02}'];center=bone.head_local.copy();lines.append([bone.head_local,bone.tail_local])
        hits={}
        for name,direction in [('palm',Vector((0,-1,0))),('back',Vector((0,1,0)))]:
            hit,normal,face,distance=tree.ray_cast(center,direction,.1)
            hits[name]={'point':list(hit) if hit else None,'distance_m':distance,'triangle':face}
        rows.append({'bone':bone.name,'head':list(bone.head_local),'tail':list(bone.tail_local),
                     'rest_matrix':[list(row) for row in bone.matrix_local],'rays':hits})
overlay=common.line_object('r009ActualRestBoneCenters',lines,(.03,.65,1),.0005)
common.render(folder,'actual-rest-centers',['palm','side','back'])
save(folder/'centerline-readback.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':clock['local_source'],
    'rig_matrix':[list(row) for row in rig.matrix_world],'object_matrix':[list(row) for row in ob.matrix_world],
    'unit_settings':{'system':bpy.context.scene.unit_settings.system,'scale_length':bpy.context.scene.unit_settings.scale_length},
    'centers':rows,'finding':'Actual ray hits andboneoverlay arediagnostic; nearest/ray surfacealone cannot establish anatomicaljoint placement. No bone moved.',
    'views':[artifact(p) for p in sorted(folder.glob('actual-rest-centers-*.png'))]})
print('R009_CENTERS '+str(len(rows)))
