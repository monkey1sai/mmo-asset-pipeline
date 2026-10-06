"""Append certified solid-angle resolution; retain the original two-ray report."""
import copy
from mathutils import Vector
from ro_hand_gate import evaluated,sword_solid
from ro_world_grasp_gate import world_contacts
from ro_solid_angle import certify_oriented_closed,classify_winding


def certified_contacts(glove,sword,rig,pads,label,parameters):
    original=world_contacts(glove,sword,rig,pads,label,parameters)
    report=copy.deepcopy(original);report['original_two_ray_report']=original
    report['supplemental_classifications']=[]
    if original['unknown_inside']:
        gp,gt,ge=evaluated(glove);sp,st,tree=sword_solid(sword)
        try:certification=certify_oriented_closed(sp,st)
        except ValueError as error:
            report['supplemental_surface_error']=str(error)
            report['method_change_not_geometry_improvement']=True
            return report
        samples={'vertex':gp,'face':[sum((gp[i] for i in t),Vector())/3 for t in gt],'edge':[(gp[a]+gp[b])/2 for a,b in ge]}
        unresolved=[];new_inside=[]
        for kind,index,reason in original['unknown_inside']:
            if reason!='parity_unknown':
                unresolved.append([kind,index,reason]);continue
            point=samples[kind][index];gap=tree.find_nearest(point)[3]
            vote,winding=classify_winding(sp,st,point,gap)
            report['supplemental_classifications'].append({'kind':kind,'index':index,'original_reason':reason,'point':list(point),
                'nearest_m':gap,'winding':winding,'inside':vote,'surface_certification':certification,
                'method_version':'oriented_exact_seam_float64_solid_angle_v1','winding_tolerance':1e-7,'near_surface_exclusion_m':1e-6})
            if vote is None:unresolved.append([kind,index,reason])
            elif vote:new_inside.append({'kind':kind,'index':index,'depth_m':gap,'point':list(point)})
        report['unknown_inside']=unresolved
        report['maximum_penetration_m']=max([original['maximum_penetration_m']]+[r['depth_m'] for r in new_inside])
        report['deep_samples']+=sum(r['depth_m']>.001 for r in new_inside)
        report['worst_penetrations']=sorted(original['worst_penetrations']+new_inside,key=lambda r:-r['depth_m'])[:12]
    report['surface_gate_pass']=not report['unknown_inside'] and report['maximum_penetration_m']<=.001 and not report['transverse_crossings_count'] and all(r['within_2mm']>=3 for r in report['pad_contacts'].values())
    report['method_change_not_geometry_improvement']=True
    return report
