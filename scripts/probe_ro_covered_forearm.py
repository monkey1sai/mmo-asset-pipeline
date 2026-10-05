"""Map actual core/armor intersections and radial coverage for all five samples."""
from pathlib import Path
import json,math,sys
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_glove_contact_ik import configure,update_wrist_helper
from ro_hand_gate import evaluated
QA=ROOT/'runs/qa/ro-swordsman-combo-r006'; out=QA/'covered-forearm-diagnosis.json'; assert not out.exists()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/processed/ro-swordsman-combo-r006/v006-wrist-loft-attempt2/ro_wrist_loft.blend'),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; bracer=bpy.data.objects['SM_RO_bracer.R']; glove=bpy.data.objects['SM_RO_glove.R']; state=json.loads(rig['state_json']); params=json.loads(rig['r006_independent_grip_ik_parameters'])
wrist=Vector(state['rest']['hand.R'][0]); axis=(wrist-Vector(state['rest']['lower_arm.R'][0])).normalized(); width=Vector(state['hand_frames']['R']['width']); u=(width-axis*axis.dot(width)).normalized(); v=axis.cross(u)
core.data.calc_loop_triangles(); bracer.data.calc_loop_triangles(); transitions=json.loads((QA/'v006-wrist-loft-attempt2/wrist-transition.json').read_text())
sets=[set(p[0] for p in row['bracer_collisions']['SM_RO_core']['pairs']) for row in transitions]; common=set.intersection(*sets); union=set.union(*sets)
face_rows=[]
for i in sorted(union):
    tri=core.data.loop_triangles[i]; centroid=sum((core.data.vertices[j].co for j in tri.vertices),Vector())/3; d=centroid-wrist; axial=d.dot(axis); radial=d-axis*axial
    influences=[{core.vertex_groups[g.group].name:g.weight for g in core.data.vertices[j].groups} for j in tri.vertices]
    face_rows.append({'triangle':i,'vertices':list(tri.vertices),'centroid_rest':list(centroid),'axial_from_wrist_m':axial,'radius_m':radial.length,'angle_deg':math.degrees(math.atan2(radial.dot(v),radial.dot(u))),
                      'intersection_samples':sum(i in s for s in sets),'common_all5':i in common,'weights':influences})
configure(rig,state,params); pose_basis={pb.name:pb.matrix_basis.copy() for pb in rig.pose.bones}; sample_coverage=[]; total_selected=[]
for vert in core.data.vertices:
    d=vert.co-wrist; t=d.dot(axis); r=(d-axis*t).length; w={core.vertex_groups[g.group].name:g.weight for g in vert.groups}
    if -.225<t<0 and r<.095 and w.get('lower_arm.R',0)>.8: total_selected.append(vert.index)
for alpha in [0,.25,.5,.75,1]:
    for pb in rig.pose.bones:
        m=pose_basis[pb.name]; b=Matrix.Identity(3).to_quaternion().slerp(m.to_quaternion(),alpha).to_matrix().to_4x4(); b.translation=m.translation*alpha; pb.matrix_basis=b
    bpy.context.view_layer.update(); update_wrist_helper(rig); glove.data.shape_keys.key_blocks['GripContact_R'].value=alpha; bpy.context.view_layer.update()
    bp,bt,_=evaluated(bracer); bvh=BVHTree.FromPolygons(bp,bt,all_triangles=True); delta=rig.pose.bones['lower_arm.R'].matrix@rig.data.bones['lower_arm.R'].matrix_local.inverted(); coverage=[]
    for i in total_selected:
        rest=core.data.vertices[i].co; d=rest-wrist; t=d.dot(axis); center=delta@(wrist+axis*t); radial=delta.to_3x3()@(d-axis*t); radial.normalize(); distances=[]; origin=center.copy(); traveled=0
        for _ in range(12):
            p,n,face,dist=bvh.ray_cast(origin,radial,.18-traveled)
            if p is None: break
            traveled+=dist; distances.append(traveled); origin=p+radial*1e-6; traveled+=1e-6
        coverage.append({'id':i,'outer_envelope_radius_m':max(distances) if distances else None,'intersection_count':len(distances)})
    sample_coverage.append({'alpha':alpha,'coverage':coverage})
all_covered=[i for i in total_selected if all(next(r for r in s['coverage'] if r['id']==i)['outer_envelope_radius_m'] is not None for s in sample_coverage)]
result={'intersection_source_triangles_union':len(union),'common_all5':len(common),'mapped_faces':face_rows,
 'proposed_local_vertex_region':total_selected,'region_definition':'own lower_arm.R weight>0.8, axial(-.225,0)m from wrist, radius<.095m; includes cut ring, excludes torso/upperarm',
 'radial_coverage_all5_vertex_ids':all_covered,'sample_radial_envelopes':sample_coverage,'covered_rebuild_hypothesis':'reduce only covered old rigid-looking core forearm bulges; taper near exposed sleeve, preserve all unrelated core and glove points',
 'interpretation':'Radial gear coverage is a design/geometry diagnostic, not a visibility or inside-solid PASS; bracer is open after trim'}
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:v for k,v in result.items() if k not in ['mapped_faces','sample_radial_envelopes','proposed_local_vertex_region','radial_coverage_all5_vertex_ids']})); print(json.dumps({'proposed_vertices':len(total_selected),'covered_all5':len(all_covered),'axial_faces_min_max':[min(r['axial_from_wrist_m'] for r in face_rows),max(r['axial_from_wrist_m'] for r in face_rows)]}))
