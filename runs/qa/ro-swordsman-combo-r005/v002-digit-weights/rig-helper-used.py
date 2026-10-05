"""Measured v002 rig helpers. Numerical constraints never imply deformation acceptance."""
import math
import bpy
from mathutils import Matrix, Vector

def assign(ob, vertex, weights):
    for group in ob.vertex_groups: group.remove([vertex.index])
    rows=sorted(((n,w) for n,w in weights.items() if w>1e-8),key=lambda x:-x[1])[:4]
    total=sum(w for n,w in rows)
    if not total: raise RuntimeError('No legal weight')
    for n,w in rows:
        g=ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)
        g.add([vertex.index],w/total,'REPLACE')

def distance(point, segment):
    h,t=map(Vector,segment); d=t-h
    along=max(0,min(1,(point-h).dot(d)/d.length_squared))
    return (point-h-d*along).length

def proximity(ob,vertex,names,rest):
    nearest=sorted(((n,distance(vertex.co,rest[n])) for n in names),key=lambda x:x[1])[:3]
    assign(ob,vertex,{n:1/max(.008,d)**4 for n,d in nearest})

def solve(head,target,a,b,pole):
    delta=Vector(target)-head; requested=delta.length
    span=min(a+b-.001,max(abs(a-b)+.001,requested)); direction=delta.normalized()
    bend=Vector(pole)-direction*direction.dot(Vector(pole))
    if bend.length<1e-6: raise RuntimeError('Degenerate pole')
    bend.normalize(); along=(a*a-b*b+span*span)/(2*span)
    return head+direction*along+bend*math.sqrt(max(0,a*a-along*along)),head+direction*span,abs(requested-span)

def aligned(rest_matrix,head,tail):
    axis=(tail-head).normalized()
    rotation=rest_matrix.to_3x3().col[1].rotation_difference(axis).to_matrix()
    out=(rotation@rest_matrix.to_3x3()).to_4x4(); out.translation=head
    return out

def apply_worlds(rig,worlds,state):
    for name in state['rest']:
        if name not in worlds: continue
        parent=state['parents'][name]; rest=rig.data.bones[name].matrix_local
        rig.pose.bones[name].matrix_basis=rest.inverted()@rig.data.bones[parent].matrix_local@worlds[parent].inverted()@worlds[name] if parent else rest.inverted()@worlds[name]
    bpy.context.view_layer.update()

def curl_digits(rig,state,side,amount):
    width=Vector(state['hand_frames'][side]['width'])
    front=Vector(state['hand_frames'][side]['front'])
    for i in range(1,5):
        angles=state.get('finger_angles',{}).get(side,{}).get(str(i),[amount,amount*1.30])
        for joint,angle in zip(('01','02'),angles):
            pb=rig.pose.bones[f'finger{i}.{side}_{joint}']; rest=rig.data.bones[pb.name].matrix_local.to_3x3()
            axis=width
            if state.get('digit_axis_method')=='individual_centerline_cross_palm':
                direction=(rig.data.bones[pb.name].tail_local-rig.data.bones[pb.name].head_local).normalized()
                axis=direction.cross(front).normalized()
            # Positive rotation about palm width sends down toward front: width x down = -front.
            pb.rotation_mode='QUATERNION'
            pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation(-angle,3,axis)@rest).to_quaternion()
    bpy.context.view_layer.update()

def oppose_thumb(rig,state,side):
    rest=state['rest']; hand=rig.pose.bones['hand.'+side]
    delta=hand.matrix@rig.data.bones[hand.name].matrix_local.inverted()
    h=delta@Vector(rest['thumb.'+side+'_01'][0])
    a=(Vector(rest['thumb.'+side+'_01'][1])-Vector(rest['thumb.'+side+'_01'][0])).length
    b=(Vector(rest['thumb.'+side+'_02'][1])-Vector(rest['thumb.'+side+'_02'][0])).length
    frame=state['hand_frames'][side]
    width=Vector(frame['width']); front=Vector(frame['front']); down=Vector(frame['down'])
    sign=-1 if side=='R' else 1
    thumb=state.get('thumb_offsets',{}).get(side,[sign*.020,.018,-.004])
    target=delta@(Vector(state['grips'][side])+width*thumb[0]+front*thumb[1]+down*thumb[2])
    pole=delta.to_3x3()@(-down)
    joint,tip,residual=solve(h,target,a,b,pole)
    worlds={hand.name:hand.matrix.copy()}
    for name,head,tail in [('thumb.'+side+'_01',h,joint),('thumb.'+side+'_02',joint,tip)]:
        posed_rest=delta@rig.data.bones[name].matrix_local
        worlds[name]=aligned(posed_rest,head,tail)
        parent=state['parents'][name]; native=rig.data.bones[name].matrix_local
        rig.pose.bones[name].matrix_basis=native.inverted()@rig.data.bones[parent].matrix_local@worlds[parent].inverted()@worlds[name]
    bpy.context.view_layer.update()
    return residual

def pose(rig,state,hip,grip_center,sword_axis,curl=.85,two_hands=True,active_side='R'):
    rest=state['rest']; parents=state['parents']; worlds={}
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    shift=Vector((0,0,hip-.89))
    for name in ['root','pelvis','spine_01','spine_02','neck','head']:
        worlds[name]=rig.data.bones[name].matrix_local.copy()
        if name!='root': worlds[name].translation+=shift
    axis=Vector(sword_axis).normalized(); feasible=Vector(grip_center); rotations={}; balls=[]
    active=['R','L'] if two_hands else [active_side]
    for side in active:
        sign=-1 if side=='R' else 1
        width=axis*sign
        front=Vector((-sign,0,0)); front-=width*front.dot(width); front.normalize()
        down=width.cross(front).normalized()
        desired=Matrix((width,front,down)).transposed()
        frame=state['hand_frames'][side]
        native=Matrix((Vector(frame['width']),Vector(frame['front']),Vector(frame['down']))).transposed()
        rotation=desired@native.transposed(); rotations[side]=rotation
        shoulder=Vector(rest['upper_arm.'+side][0])+shift
        h,t=map(Vector,rest['upper_arm.'+side]); a=(t-h).length
        h,t=map(Vector,rest['lower_arm.'+side]); b=(t-h).length
        offset=rotation@(Vector(state['grips'][side])-h)
        stack=axis*.095 if side=='L' and two_hands else Vector((0,0,0))
        balls.append((shoulder+offset+stack,a+b-.002))
    for _ in range(80):
        for center,radius in balls:
            d=feasible-center
            if d.length>radius: feasible=center+d.normalized()*radius
    if any((feasible-c).length>r+.00001 for c,r in balls): raise RuntimeError('No common reachable grip')
    if (feasible-Vector(grip_center)).length>.10: raise RuntimeError('Requested pose needs excessive grip displacement')
    residuals={}
    for side,sign in [('R',-1),('L',1)]:
        shoulder=Vector(rest['upper_arm.'+side][0])+shift
        for name in ['clavicle.'+side]:
            worlds[name]=rig.data.bones[name].matrix_local.copy(); worlds[name].translation+=shift
        if side in active:
            rotation=rotations[side]; grip=feasible-(axis*.095 if side=='L' and two_hands else Vector((0,0,0)))
            wrist_target=grip-rotation@(Vector(state['grips'][side])-Vector(rest['hand.'+side][0]))
            a=(Vector(rest['upper_arm.'+side][1])-Vector(rest['upper_arm.'+side][0])).length
            b=(Vector(rest['lower_arm.'+side][1])-Vector(rest['lower_arm.'+side][0])).length
            elbow,wrist,residuals[side]=solve(shoulder,wrist_target,a,b,(sign*.8,-.5,.05))
            worlds['upper_arm.'+side]=aligned(rig.data.bones['upper_arm.'+side].matrix_local,shoulder,elbow)
            worlds['lower_arm.'+side]=aligned(rig.data.bones['lower_arm.'+side].matrix_local,elbow,wrist)
            hand=(rotation@rig.data.bones['hand.'+side].matrix_local.to_3x3()).to_4x4(); hand.translation=wrist
            worlds['hand.'+side]=hand
        else:
            for name in ['upper_arm.'+side,'lower_arm.'+side,'hand.'+side]:
                worlds[name]=rig.data.bones[name].matrix_local.copy(); worlds[name].translation+=shift
        h=Vector(rest['upper_leg.'+side][0])+shift; target=Vector(rest['lower_leg.'+side][1])
        a=(Vector(rest['upper_leg.'+side][1])-Vector(rest['upper_leg.'+side][0])).length
        b=(Vector(rest['lower_leg.'+side][1])-Vector(rest['lower_leg.'+side][0])).length
        knee,ankle,residuals['foot.'+side]=solve(h,target,a,b,(0,-1,0))
        worlds['upper_leg.'+side]=aligned(rig.data.bones['upper_leg.'+side].matrix_local,h,knee)
        worlds['lower_leg.'+side]=aligned(rig.data.bones['lower_leg.'+side].matrix_local,knee,ankle)
        for name in ['foot.'+side,'toe.'+side]: worlds[name]=rig.data.bones[name].matrix_local.copy()
        arm_delta=worlds['upper_arm.'+side].to_quaternion()@rig.data.bones['upper_arm.'+side].matrix_local.to_quaternion().inverted()
        paul=(arm_delta.slerp(Matrix.Identity(3).to_quaternion(),.55).to_matrix()@rig.data.bones['pauldron.'+side].matrix_local.to_3x3()).to_4x4()
        paul.translation=shoulder; worlds['pauldron.'+side]=paul
        coat=(Matrix.Rotation(max(0,(.89-hip)*3.3),3,'X')@rig.data.bones['coat.'+side].matrix_local.to_3x3()).to_4x4()
        coat.translation=Vector(rest['coat.'+side][0])+shift; worlds['coat.'+side]=coat
    worlds['tabard']=rig.data.bones['tabard'].matrix_local.copy(); worlds['tabard'].translation+=shift
    if active_side=='L' and not two_hands:
        worlds['sword']=aligned(rig.data.bones['sword'].matrix_local,feasible,feasible+axis*.8)
    apply_worlds(rig,worlds,state)
    for side in active:
        curl_digits(rig,state,side,curl)
        residuals['thumb.'+side]=oppose_thumb(rig,state,side)
    return {'requested_grip':list(grip_center),'feasible_grip':list(feasible),'grip_adjustment_m':(feasible-Vector(grip_center)).length,'bone_target_residual_m':residuals,'surface_contact_accepted':False}
