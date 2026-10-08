"""Rest-space rotation transfer, independent of names, games and DCC.

Input matrices share an armature coordinate system, in metres. Source bind and
target bind remain immutable. No scale transfer, no target bone additions.
"""
import numpy as np


def validate_rig_document(document, required_names):
    nodes=document.get('nodes',[]);skins=document.get('skins',[])
    if len(skins)!=1:raise ValueError('RIG_SKIN_COUNT')
    joints=skins[0].get('joints',[])
    if not joints or len(joints)!=len(set(joints)) or any(type(i) is not int or not 0<=i<len(nodes) for i in joints):
        raise ValueError('RIG_JOINT_INDEX')
    names=[nodes[i].get('name') for i in joints]
    if any(not isinstance(n,str) or not n for n in names) or len(names)!=len(set(names)):
        raise ValueError('RIG_BONE_AMBIGUOUS')
    if not set(required_names)<=set(names):raise ValueError('RIG_BONE_MISSING')
    for name in required_names:
        if sum(n.get('name')==name for n in nodes)!=1:raise ValueError('RIG_BONE_AMBIGUOUS')


def validate_export_channels(document, mapped_names, secondary_names):
    allowed=set(mapped_names);secondary=set(secondary_names)
    if not allowed or allowed&secondary:raise ValueError('BONE_WRITER_CONFLICT')
    validate_rig_document(document,allowed|secondary)
    animations=document.get('animations',[])
    if len(animations)!=1 or not animations[0].get('channels'):raise ValueError('EXPORT_CLIP_COUNT')
    seen=set();targets=set();nodes=document['nodes']
    for channel in animations[0]['channels']:
        target=channel.get('target',{});index=target.get('node');path=target.get('path')
        if type(index) is not int or not 0<=index<len(nodes) or path not in ('translation','rotation','scale'):
            raise ValueError('EXPORT_CHANNEL_TARGET')
        name=nodes[index].get('name')
        if name not in allowed:raise ValueError('EXPORT_UNOWNED_BONE_TRACK')
        key=(index,path)
        if key in seen:raise ValueError('EXPORT_DUPLICATE_CHANNEL')
        seen.add(key);targets.add(name)
    if targets!=allowed:raise ValueError('EXPORT_MAPPED_BONE_MISSING')
    return {'status':'PASS','animation_count':1,'channel_count':len(seen),'animated_bones':sorted(targets)}


def validate_source_clip(document, declared_names):
    animations=document.get('animations',[])
    if len(animations)!=1 or not animations[0].get('channels'):raise ValueError('SOURCE_CLIP_COUNT')
    if declared_names!=[animations[0].get('name')]:raise ValueError('SOURCE_CLIP_BINDING')


def rigid_matrix(value):
    m=np.asarray(value,dtype=float)
    if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1]):
        raise ValueError('MATRIX_INVALID')
    if not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3),atol=1e-5) or np.linalg.det(m[:3,:3])<0:
        raise ValueError('NON_RIGID_POSE')
    return m


def retarget(source_rest, source_pose, target_rest, mapping, *, basis=None,
             root_policy='in_place', root_target=None, translation_scale=1., target_parents=None):
    if root_policy not in ('in_place','root_motion'):
        raise ValueError('ROOT_POLICY')
    if type(translation_scale) not in (int,float) or not np.isfinite(translation_scale) or translation_scale<=0:
        raise ValueError('TRANSLATION_SCALE')
    if not mapping or len(set(mapping.values()))!=len(mapping):
        raise ValueError('MAP_COLLISION')
    if root_policy=='root_motion' and root_target not in mapping.values():
        raise ValueError('ROOT_TARGET_REQUIRED')
    b=rigid_matrix(np.eye(4) if basis is None else basis)[:3,:3]
    result={name:rigid_matrix(m).copy() for name,m in target_rest.items()}
    for s,t in mapping.items():
        rest=rigid_matrix(source_rest[s]); pose=rigid_matrix(source_pose[s]); dest=result[t]
        delta=pose[:3,:3]@rest[:3,:3].T
        dest[:3,:3]=b@delta@b.T@dest[:3,:3]
        if root_policy=='root_motion' and t==root_target:
            dest[:3,3]+=b@(pose[:3,3]-rest[:3,3])*translation_scale
    if target_parents is not None:
        if set(target_parents)!=set(target_rest):raise ValueError('PARENT_LAYOUT')
        done=set();visiting=set();mapped=set(mapping.values())
        def place(name):
            if name in done:return
            if name in visiting:raise ValueError('PARENT_CYCLE')
            visiting.add(name);parent=target_parents[name]
            if parent is not None:
                if parent not in result:raise ValueError('PARENT_MISSING')
                place(parent)
                delta=result[parent]@np.linalg.inv(rigid_matrix(target_rest[parent]))
                result[name][:3,3]=(delta@rigid_matrix(target_rest[name]))[:3,3]
                if name not in mapped:result[name][:3,:3]=(delta@rigid_matrix(target_rest[name]))[:3,:3]
            visiting.remove(name);done.add(name)
        for name in result:place(name)
    return result
