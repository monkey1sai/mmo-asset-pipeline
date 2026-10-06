"""Pose a character V1 armature into a joint-range contract motion (Blender side).

Same direction and rotation rules as scripts/cv1_joint_range.py, which keeps its own copy so the frozen
measurement tool does not change when this module does.
"""
import math

from mathutils import Quaternion, Vector

HAND_DIRECTIONS = ("palmar", "dorsal", "radial", "ulnar")


class ContractPoser:
    def __init__(self, arm, contract, poses=None):
        self.arm, self.bones, self.contract = arm, arm.data.bones, contract
        self.motions = {m["id"]: m for m in contract["motions"]}
        self.poses = poses or {}
        self.axes = {name: Vector(value) for name, value in contract["axes"].items()}
        names = contract["hand_landmarks"]
        self.hands = {side: self._hand_frame(side) for side in ("L", "R")
                      if names["hand"].format(side=side) in self.bones and names["thumb_base"].format(side=side) in self.bones
                      and all(names["finger_base"].format(i=i, side=side) in self.bones for i in (1, 2, 3, 4))}

    def _hand_frame(self, side):
        names, bones = self.contract["hand_landmarks"], self.bones
        mcp = {i: bones[names["finger_base"].format(i=i, side=side)].head_local for i in (1, 2, 3, 4)}
        wrist = bones[names["hand"].format(side=side)].head_local
        thumb = bones[names["thumb_base"].format(side=side)].head_local
        index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
        along = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
        across = mcp[index] - mcp[pinky]
        radial = (across - along * across.dot(along)).normalized()
        palmar = radial.cross(along) if side == "R" else along.cross(radial)
        return {"palmar": palmar.normalized(), "dorsal": -palmar.normalized(), "radial": radial, "ulnar": -radial}

    def direction(self, name, side):
        if name in ("out", "in"):
            lateral = self.axes["left"] if side == "L" else -self.axes["left"]
            return lateral if name == "out" else -lateral
        if name in ("forward", "back"):
            return self.axes["forward"] if name == "forward" else -self.axes["forward"]
        if name in ("up", "down"):
            return self.axes["up"] if name == "up" else -self.axes["up"]
        if name in ("left", "right"):
            return self.axes["left"] if name == "left" else -self.axes["left"]
        return self.hands[side][name]

    def step_rotation(self, step, side, level):
        bone = self.bones[step["bone"]]
        if step["kind"] == "swing":
            axis = (bone.tail_local - bone.head_local).normalized().cross(self.direction(step["toward"], side))
        elif "about_bone" in step:
            about = self.bones[step["about_bone"]]
            axis = about.tail_local - about.head_local
        else:
            axis = self.direction(step["about"], side)
        if axis.length < 1e-6:
            raise ValueError(f"DEGENERATE_AXIS {step}")
        return Quaternion(bone.matrix_local.to_3x3().inverted() @ axis.normalized(), math.radians(step["degrees"]) * level)

    def reset(self):
        for pb in self.arm.pose.bones:
            pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)

    def apply(self, motion_id, level):
        """Rest pose, then the candidate pose the motion requires, then the motion's steps at the given level."""
        motion = self.motions[motion_id]
        self.reset()
        if motion.get("requires_pose"):
            for name, quaternion in self.poses[motion["requires_pose"]].items():
                self.arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        for step in motion["steps"]:
            pb = self.arm.pose.bones[step["bone"]]
            pb.rotation_quaternion = pb.rotation_quaternion @ self.step_rotation(step, step.get("side", motion.get("side")), level)
        return motion.get("state", {})


def pose_rel(arm):
    """Rest-relative local rotation of every bone from evaluated pose matrices, (w, x, y, z)."""
    out = {}
    for pb in arm.pose.bones:
        rest = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        out[pb.name] = tuple((rest.inverted() @ local).to_quaternion())
    return out
