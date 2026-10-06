"""Use original contact thresholds with sword bone and mesh in world space."""
from types import SimpleNamespace
from ro_hand_gate import contacts


def world_contacts(glove, sword, rig, pads, label, parameters):
    bone = rig.pose.bones['sword']
    world_bone = SimpleNamespace(head=rig.matrix_world @ bone.head,
                                 tail=rig.matrix_world @ bone.tail)
    frame = SimpleNamespace(pose=SimpleNamespace(bones={'sword': world_bone}))
    return contacts(glove, sword, frame, pads, label, parameters)
