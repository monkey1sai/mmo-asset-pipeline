"""Analytic two-bone arm IK for character V1 clip authoring (Blender side).

Same method as scripts/cv1_two_hand_pose.py (which authored the frozen two-hand chop pose and is left unchanged):
the hand bone gets a target matrix, the elbow is the two-bone solution turned by a swivel about the shoulder-wrist
line, the upper and lower arm swing onto the shoulder-elbow and elbow-wrist lines, and the hand takes the target.
Twist carriers are not set here; the runtime rule (helpers) drives them from the final hand pose.

solve_hinge() puts the elbow at the same point but keeps the elbow a hinge: the lower arm turns only about the
joint-range contract's flexion axis (scripts/cv1_contract_pose.py, lower_arm "twist about right"), from rest up to the
contract's flexion extreme, and the upper arm takes the humeral turn that lays that hinge in the arm plane. Forearm
rotation (pronation, supination) is then all in the hand bone, the way the contract moves it.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

# Contract "right" direction (joint-range contract axes: left = +X), elbow-flexion and forearm-rotation extremes
# (joint-range contract v5 and request support_envelope: elbow flexion 135, pronation and supination 70 degrees). A
# contract passed to ArmIK replaces the two extremes with its own extreme-level values.
RIGHT = Vector((-1.0, 0.0, 0.0))
ELBOW_FLEXION_MAX_DEG = 135.0
PRONATION_MAX_DEG = 70.0
BOUNDARY_TOLERANCE_RAD = 1e-6


def frame(primary, secondary):
    """Orthonormal basis (columns): primary, the part of secondary across it, and their cross product."""
    a = primary.normalized()
    b = (secondary - a * secondary.dot(a)).normalized()
    return Matrix((a, b, a.cross(b))).transposed()


def sword_world(grip, blade, roll):
    """Sword bone matrix with its origin on the grip point, its axis on the blade direction and a roll about that axis."""
    blade = blade.normalized()
    side = blade.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
    up = side.cross(blade).normalized()
    x_axis = side * math.cos(roll) + up * math.sin(roll)
    z_axis = x_axis.cross(blade).normalized()
    return Matrix.Translation(grip) @ Matrix((x_axis, blade, z_axis)).transposed().to_4x4()


def swing_twist(q, axis):
    """Signed twist angle (radians, wrapped to [-pi, pi]) of q about the unit axis, and the remaining swing quaternion."""
    along = Vector((q.x, q.y, q.z)).dot(axis)
    twist = math.atan2(along, q.w) * 2 if abs(along) + abs(q.w) > 1e-12 else 0.0
    twist = (twist + math.pi) % (2 * math.pi) - math.pi
    return twist, q @ Quaternion(axis, twist).inverted()


class ArmIK:
    def __init__(self, arm, contract=None):
        self.arm, bones = arm, arm.data.bones
        self.bones = bones
        self.shoulder_rest = {side: bones[f"upper_arm.{side}"].head_local.copy() for side in "RL"}
        self.length = {side: ((bones[f"lower_arm.{side}"].head_local - bones[f"upper_arm.{side}"].head_local).length,
                              (bones[f"hand.{side}"].head_local - bones[f"lower_arm.{side}"].head_local).length) for side in "RL"}
        self.rest = {side: {name: bones[f"{name}.{side}"].matrix_local.to_3x3() for name in ("upper_arm", "lower_arm", "hand")} for side in "RL"}
        if "sword" in bones:
            self.sword_relative = bones["hand.R"].matrix_local.inverted() @ bones["sword"].matrix_local
        self.flexion_max_deg, self.pronation_max_deg = ELBOW_FLEXION_MAX_DEG, PRONATION_MAX_DEG
        if contract is not None:
            level = max(contract["levels"].values())
            motions = {m["id"]: m for m in contract["motions"]}
            self.flexion_max_deg = abs(motions["elbow-flexion.R"]["steps"][0]["degrees"]) * level
            self.pronation_max_deg = abs(motions["forearm-pronation.R"]["steps"][0]["degrees"]) * level
        self.hinge = {}
        for side in "RL":
            upper0, lower0, hand0 = (self.rest[side][name] for name in ("upper_arm", "lower_arm", "hand"))
            elbow = bones[f"lower_arm.{side}"].head_local
            self.hinge[side] = {
                "axis": (lower0.inverted() @ RIGHT).normalized(),  # flexion axis in the lower arm's rest frame
                "elbow": upper0.inverted() @ (elbow - self.shoulder_rest[side]),  # elbow in the upper arm's frame
                "relation": upper0.inverted() @ lower0,  # rest lower arm in the upper arm's frame
                "wrist": lower0.inverted() @ (bones[f"hand.{side}"].head_local - elbow),  # wrist in the lower arm's frame
                "hand": lower0.inverted() @ hand0,  # rest hand in the lower arm's frame
                "pronation_axis": (hand0.inverted() @ (bones[f"lower_arm.{side}"].tail_local - elbow)).normalized(),
            }

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

    def flexion_for(self, side, distance):
        """Hinge angle (radians, positive flexes) that puts the wrist `distance` from the shoulder.

        With the lower arm turned by theta about the hinge, the squared shoulder-wrist distance is c + r cos(theta - phi);
        it falls as the elbow flexes from straight (phi) to fully folded (phi + pi). Raises ValueError outside rest..extreme.
        """
        g = self.hinge[side]
        axis, wrist = g["axis"], g["wrist"]
        elbow_seen = g["relation"].transposed() @ g["elbow"]
        along = axis * axis.dot(wrist)
        across = wrist - along
        c = g["elbow"].length_squared + wrist.length_squared + 2 * elbow_seen.dot(along)
        p, q = 2 * elbow_seen.dot(across), 2 * elbow_seen.dot(axis.cross(across))
        x = (distance * distance - c) / math.hypot(p, q)
        if abs(x) > 1.0:
            raise ValueError(f"OUT_OF_REACH {side} (hinge cannot reach {distance:.4f} m)")
        theta = math.atan2(q, p) + math.acos(x)
        extreme = math.radians(self.flexion_max_deg)
        if theta < -BOUNDARY_TOLERANCE_RAD:
            raise ValueError(f"OUT_OF_REACH {side} (needs the elbow {math.degrees(-theta):.6f} deg past rest extension)")
        if theta > extreme + BOUNDARY_TOLERANCE_RAD:
            raise ValueError(f"ELBOW_FLEXION_OVER_CONTRACT {side} {math.degrees(theta):.4f} > {self.flexion_max_deg} deg")
        return min(max(theta, 0.0), extreme)  # float noise at the rest and extreme boundaries

    def hinge_frames(self, side, target, swivel_deg, shoulder=None):
        """Upper and lower arm rotations (armature space) of the hinge solution, and its flexion; ValueError when unreachable."""
        shoulder = self.shoulder(side) if shoulder is None else shoulder
        wrist = target.translation
        theta = self.flexion_for(side, (wrist - shoulder).length)
        elbow = self.elbow_of(side, wrist, math.radians(swivel_deg), shoulder)
        if elbow is None:
            raise ValueError(f"OUT_OF_REACH {side}")
        g = self.hinge[side]
        bend = Matrix.Rotation(theta, 3, g["axis"])
        local_wrist = g["elbow"] + g["relation"] @ (bend @ g["wrist"])
        # The upper arm takes the shoulder-wrist line and lays the elbow on the swivelled pole side: same elbow point as solve().
        upper = frame(wrist - shoulder, elbow - shoulder) @ frame(local_wrist, g["elbow"]).transposed()
        return upper, upper @ g["relation"] @ bend, theta

    def hand_relation(self, side, lower, target):
        """Hand rotation against the lower arm (rest-relative), split into pronation (+) / supination (-) and the rest."""
        g = self.hinge[side]
        q = ((lower @ g["hand"]).inverted() @ target.to_3x3()).to_quaternion()
        twist, swing = swing_twist(q, g["pronation_axis"])
        return {"pronation_deg": math.degrees(twist), "wrist_swing_deg": math.degrees(swing.angle), "wrist_bend_deg": math.degrees(q.angle),
                "pronation_over_contract": abs(math.degrees(twist)) > self.pronation_max_deg}

    def best_hinge_swivel(self, side, target, swivels_deg=tuple(range(-60, 61, 10))):
        """(wrist bend, swivel) of the hinge solution with the least wrist bend; None when no swivel reaches."""
        options = []
        for s in swivels_deg:
            try:
                _, lower, _ = self.hinge_frames(side, target, s)
            except ValueError:
                continue
            options.append((self.hand_relation(side, lower, target)["wrist_bend_deg"], s))
        return min(options) if options else None

    def solve_hinge(self, side, target, swivel_deg, relax=0.0):
        """Pose the arm so the hand bone matrix equals target with the elbow as a pure hinge; returns solve diagnostics.

        relax (0..1) turns the hand from the target orientation toward its rest relation to the forearm (slerp; the wrist
        point stays on the target), so pronation and wrist bend shrink together, e.g. a hand that has let go.
        """
        if not 0.0 <= relax <= 1.0:
            raise ValueError(f"HAND_RELAX_RANGE {relax} (0..1)")
        arm = self.arm
        upper, lower, hand = (arm.pose.bones[f"{name}.{side}"] for name in ("upper_arm", "lower_arm", "hand"))
        shoulder = self.shoulder(side)
        upper_frame, lower_frame, theta = self.hinge_frames(side, target, swivel_deg, shoulder)
        if relax > 0.0:
            neutral = (lower_frame @ self.hinge[side]["hand"]).to_quaternion()
            target = Matrix.Translation(target.translation) @ target.to_quaternion().slerp(neutral, relax).to_matrix().to_4x4()
        upper.matrix = Matrix.Translation(shoulder) @ upper_frame.to_4x4()
        upper.location = (0, 0, 0)
        bpy.context.view_layer.update()
        lower.rotation_mode = "QUATERNION"
        lower.rotation_quaternion = Quaternion(self.hinge[side]["axis"], theta)
        lower.location = (0, 0, 0)
        bpy.context.view_layer.update()
        hand.matrix = target
        hand.location = (0, 0, 0)
        bpy.context.view_layer.update()
        elbow, wrist = lower.head.copy(), target.translation
        posed = lower.matrix.to_3x3()
        # Humeral rotation the hinge asks of the shoulder: upper arm against its rest relation to the clavicle, split into
        # the turn about its own axis and the swing of that axis.
        rest_local = upper.bone.parent.matrix_local.to_3x3().inverted() @ upper.bone.matrix_local.to_3x3()
        local = upper.parent.matrix.to_3x3().inverted() @ upper.matrix.to_3x3()
        humeral, humeral_swing = swing_twist((rest_local.inverted() @ local).to_quaternion(), Vector((0.0, 1.0, 0.0)))
        return dict(self.hand_relation(side, posed, target), wrist_error_mm=(hand.matrix.translation - wrist).length * 1e3,
                    upper_twist_deg=math.degrees(humeral), upper_swing_deg=math.degrees(humeral_swing.angle),
                    lower_frame_error_deg=math.degrees(posed.to_quaternion().rotation_difference(lower_frame.to_quaternion()).angle),
                    elbow_angle_deg=math.degrees((shoulder - elbow).angle(wrist - elbow)), flexion_deg=math.degrees(theta), swivel_deg=swivel_deg,
                    relax=relax)


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
