"""Replay archived v003 independently solved contact pose for a given rig/state."""
import math
import bpy
from mathutils import Matrix,Vector
from ro_core_rig import pose,solve,aligned

def update_wrist_helper(rig):
    n='wrist_transition.R'
    if n not in rig.data.bones:
        return
    forearm='lower_arm.R'; hand='hand.R'
    a=rig.pose.bones[forearm].matrix@rig.data.bones[forearm].matrix_local.inverted()
    b=rig.pose.bones[hand].matrix@rig.data.bones[hand].matrix_local.inverted()
    rotation=a.to_quaternion().slerp(b.to_quaternion(),.5)
    desired=(rotation.to_matrix()@rig.data.bones[n].matrix_local.to_3x3()).to_4x4()
    desired.translation=rig.pose.bones[hand].head
    rig.pose.bones[n].matrix_basis=rig.data.bones[n].matrix_local.inverted()@rig.data.bones[forearm].matrix_local@rig.pose.bones[forearm].matrix.inverted()@desired
    bpy.context.view_layer.update()

def configure(rig,state,params):
    front=Vector(state['hand_frames']['R']['front']); down=Vector(state['hand_frames']['R']['down']); width=Vector(state['hand_frames']['R']['width'])
    fixture=pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),curl=.85,two_hands=False)
    hand=rig.pose.bones['hand.R']; delta=hand.matrix@rig.data.bones['hand.R'].matrix_local.inverted()
    f=(delta.to_3x3()@front).normalized(); d=(delta.to_3x3()@down).normalized(); w=(delta.to_3x3()@width).normalized()
    center=rig.pose.bones['sword'].head.copy(); worlds={'hand.R':hand.matrix.copy()}; residuals={}
    def put(rows):
        for n,m in rows.items():
            if n=='hand.R': continue
            parent=state['parents'][n]; parent_world=rows[parent] if parent in rows else rig.pose.bones[parent].matrix
            rig.pose.bones[n].matrix_basis=rig.data.bones[n].matrix_local.inverted()@rig.data.bones[parent].matrix_local@parent_world.inverted()@m
        bpy.context.view_layer.update()
    for i in range(1,5):
        names=[f'finger{i}.R_{j:02}' for j in [1,2,3]]; h=delta@Vector(state['rest'][names[0]][0])
        lengths=[(Vector(state['rest'][n][1])-Vector(state['rest'][n][0])).length for n in names]
        c=center+w*(h-center).dot(w); r=params['radius']; phi=math.radians(params['phis'][i-1])
        p2=c+f*(r*math.cos(phi))+d*(r*math.sin(phi)); p1,reached,residual=solve(h,p2,lengths[0],lengths[1],-f)
        arc=2*math.asin(min(.99,lengths[2]/(2*r))); desired3=c+f*(r*math.cos(phi-arc))+d*(r*math.sin(phi-arc))
        p3=reached+(desired3-reached).normalized()*lengths[2]
        residuals[f'finger{i}']={'p2_target_residual_m':residual,'centerline_radius_m':r,'arc_degrees':math.degrees(arc)}
        for n,a,b in zip(names,[h,p1,reached],[p1,reached,p3]): worlds[n]=aligned(delta@rig.data.bones[n].matrix_local,a,b)
    put(worlds)
    names=['thumb.R_01','thumb.R_02']; h=delta@Vector(state['rest'][names[0]][0])
    a,b=[(Vector(state['rest'][n][1])-Vector(state['rest'][n][0])).length for n in names]
    target=center+w*params['thumb_width']+f*params['thumb_front']+d*params['thumb_down']; mid,tip,residual=solve(h,target,a,b,-d)
    worlds={'hand.R':hand.matrix.copy()}
    for n,a,b in zip(names,[h,mid],[mid,tip]):
        m=aligned(delta@rig.data.bones[n].matrix_local,a,b)
        if n.endswith('02'):
            axis=m.to_3x3().col[1].normalized(); old=(m@rig.data.bones[n].matrix_local.inverted()).to_3x3()@front
            old-=axis*old.dot(axis); new=center-(a+b)/2; new-=axis*new.dot(axis)
            if old.length>1e-6 and new.length>1e-6:
                old.normalize(); new.normalize(); angle=math.atan2(axis.dot(old.cross(new)),old.dot(new))
                adjusted=(Matrix.Rotation(angle,3,axis)@m.to_3x3()).to_4x4(); adjusted.translation=m.translation; m=adjusted
        worlds[n]=m
    put(worlds); update_wrist_helper(rig)
    fixture['independent_joint_targets']=residuals; fixture['thumb_target_residual_m']=residual
    return fixture
