"""Analytic two-bone arm IK for character V1 clip authoring (Blender side).

Same method as scripts/cv1_two_hand_pose.py (which authored the frozen two-hand chop pose and is left unchanged):
the hand bone gets a target matrix, the elbow is the two-bone solution turned by a swivel about the shoulder-wrist
line, the upper and lower arm swing onto the shoulder-elbow and elbow-wrist lines, and the hand takes the target.
Twist carriers are not set here; the runtime rule (helpers) drives them from the final hand pose.
"""
import math

import bpy
from mathutils import Matrix, Vector


def sword_world(grip, blade, roll):
    """Sword bone matrix with its origin on the grip point, its axis on the blade direction and a roll about that axis."""
    blade = blade.normalized()
    side = blade.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
    up = side.cross(blade).normalized()
    x_axis = side * math.cos(roll) + up * math.sin(roll)
    z_axis = x_axis.cross(blade).normalized()
    return Matrix.Translation(grip) @ Matrix((x_axis, blade, z_axis)).transposed().to_4x4()


class ArmIK:
    def __init__(self, arm):
        self.arm, bones = arm, arm.data.bones
        self.bones = bones
        self.shoulder_rest = {side: bones[f"upper_arm.{side}"].head_local.copy() for side in "RL"}
        self.length = {side: ((bones[f"lower_arm.{side}"].head_local - bones[f"upper_arm.{side}"].head_local).length,
                              (bones[f"hand.{side}"].head_local - bones[f"lower_arm.{side}"].head_local).length) for side in "RL"}
        self.rest = {side: {name: bones[f"{name}.{side}"].matrix_local.to_3x3() for name in ("upper_arm", "lower_arm", "hand")} for side in "RL"}
        if "sword" in bones:
            self.sword_relative = bones["hand.R"].matrix_local.inverted() @ bones["sword"].matrix_local

    def shoulder(self, side):
        """Current (posed) shoulder joint in armature space."""
        return self.arm.pose.bones[f"upper_arm.{side}"].head.copy()

    def elbow_of(self, side, wrist, swivel=0.0, shoulder=None):
        """Elbow of the two-bone solution, below and outside the shoulder-wrist line, turned by swivel; None when out of reach."""
        shoulder = self.shoulder(side) if shoulder is None else shoulder
        l1, l2 = self.length[side]
        line = wrist - shoulder
        d = line.length
        if d > (l1 + l2) * 0.985 or d < abs(l1 - l2) * 1.05:
            return None
        direction = line / d
        a1 = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, l1 * l1 - a1 * a1))
        out_side = Vector((1, 0, 0)) if side == "L" else Vector((-1, 0, 0))
        pole = Vector((0, 0, -1)) + out_side * 0.6 + Vector((0, 0.3, 0))
        pole = (pole - direction * pole.dot(direction)).normalized()
        pole = Matrix.Rotation(swivel if side == "R" else -swivel, 3, direction) @ pole
        return shoulder + direction * a1 + pole * h

    def wrist_bend_deg(self, side, target, elbow, shoulder=None):
        """Angle of the hand's rotation away from its rest relation to the forearm after the arm swings onto the solution."""
        shoulder = self.shoulder(side) if shoulder is None else shoulder
        upper_swing = self.rest[side]["upper_arm"].col[1].rotation_difference((elbow - shoulder).normalized()).to_matrix()
        lower_swing = (upper_swing @ self.rest[side]["lower_arm"].col[1]).rotation_difference((target.translation - elbow).normalized()).to_matrix()
        carried = lower_swing @ upper_swing @ self.rest[side]["hand"]
        return math.degrees((carried.inverted() @ target.to_3x3()).to_quaternion().angle)

    def best_swivel(self, side, target, swivels_deg=tuple(range(-60, 61, 10))):
        options = [(self.wrist_bend_deg(side, target, elbow), s) for s in swivels_deg
                   if (elbow := self.elbow_of(side, target.translation, math.radians(s))) is not None]
        return min(options) if options else None

    def solve(self, side, target, swivel_deg):
        """Pose upper arm, lower arm and hand so the hand bone matrix equals target; returns solve diagnostics."""
        arm = self.arm
        upper, lower, hand = (arm.pose.bones[f"{name}.{side}"] for name in ("upper_arm", "lower_arm", "hand"))
        shoulder = self.shoulder(side)
        wrist = target.translation
        elbow = self.elbow_of(side, wrist, math.radians(swivel_deg), shoulder)
        if elbow is None:
            raise ValueError(f"OUT_OF_REACH {side}")
        for pose_bone, start, end in ((upper, shoulder, elbow), (lower, elbow, wrist)):
            current = pose_bone.matrix.copy()
            swing = current.to_3x3().col[1].rotation_difference((end - start).normalized()).to_matrix()
            pose_bone.matrix = Matrix.Translation(start) @ (swing @ current.to_3x3()).to_4x4()
            pose_bone.location = (0, 0, 0)
            bpy.context.view_layer.update()
        hand.matrix = target
        hand.location = (0, 0, 0)
        bpy.context.view_layer.update()
        return {"wrist_error_mm": (hand.matrix.translation - wrist).length * 1e3, "elbow_angle_deg": math.degrees((shoulder - elbow).angle(wrist - elbow)),
                "wrist_bend_deg": self.wrist_bend_deg(side, target, elbow, shoulder), "swivel_deg": swivel_deg}

    def hand_for_sword(self, sword_matrix):
        """Right-hand bone matrix that puts the sword bone on sword_matrix with the verified grip (weapon socket unchanged)."""
        return sword_matrix @ self.sword_relative.inverted()


class LegIK:
    """Two-bone leg IK: upper and lower leg swing onto hip-knee-ankle, the knee forward (slightly out); the foot takes a target matrix."""

    def __init__(self, arm, reach=0.995):
        self.arm, bones = arm, arm.data.bones
        self.reach = reach
        self.length = {side: ((bones[f"lower_leg.{side}"].head_local - bones[f"upper_leg.{side}"].head_local).length,
                              (bones[f"foot.{side}"].head_local - bones[f"lower_leg.{side}"].head_local).length) for side in "RL"}
        self.foot_rest = {side: bones[f"foot.{side}"].matrix_local.copy() for side in "RL"}
        self.hip_rest = {side: bones[f"upper_leg.{side}"].head_local.copy() for side in "RL"}

    def hip(self, side):
        return self.arm.pose.bones[f"upper_leg.{side}"].head.copy()

    def max_length(self, side):
        return sum(self.length[side]) * self.reach

    def knee_of(self, side, ankle, hip=None, pole_yaw_deg=0.0):
        """pole_yaw_deg turns the knee direction outward (toe-out gait: the thigh rotates externally)."""
        hip = self.hip(side) if hip is None else hip
        l1, l2 = self.length[side]
        line = ankle - hip
        d = line.length
        if d > (l1 + l2) * self.reach or d < abs(l1 - l2) * 1.05:
            return None
        direction = line / d
        a1 = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, l1 * l1 - a1 * a1))
        out_side = Vector((1, 0, 0)) if side == "L" else Vector((-1, 0, 0))
        pole = Vector((0, -1, 0)) + out_side * 0.1
        if pole_yaw_deg:
            pole = Matrix.Rotation(math.radians(pole_yaw_deg if side == "L" else -pole_yaw_deg), 3, Vector((0, 0, 1))) @ pole
        pole = (pole - direction * pole.dot(direction)).normalized()
        return hip + direction * a1 + pole * h

    def solve(self, side, foot_matrix, pole_yaw_deg=0.0):
        arm = self.arm
        upper, lower, foot = (arm.pose.bones[f"{name}.{side}"] for name in ("upper_leg", "lower_leg", "foot"))
        hip, ankle = self.hip(side), foot_matrix.translation.copy()
        knee = self.knee_of(side, ankle, hip, pole_yaw_deg)
        if knee is None:
            raise ValueError(f"LEG_OUT_OF_REACH {side} {(ankle - hip).length:.4f} > {self.max_length(side):.4f}")
        for pose_bone, start, end in ((upper, hip, knee), (lower, knee, ankle)):
            current = pose_bone.matrix.copy()
            swing = current.to_3x3().col[1].rotation_difference((end - start).normalized()).to_matrix()
            pose_bone.matrix = Matrix.Translation(start) @ (swing @ current.to_3x3()).to_4x4()
            pose_bone.location = (0, 0, 0)
            bpy.context.view_layer.update()
        foot.matrix = foot_matrix
        foot.location = (0, 0, 0)
        bpy.context.view_layer.update()
        return {"ankle_error_mm": (foot.matrix.translation - ankle).length * 1e3, "knee_angle_deg": math.degrees((hip - knee).angle(ankle - knee))}
