"""Two-hand pose search: score the whole wrist rotation (bend and twist) and let the elbows swivel.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-pose-wrist-used.py
The earlier score only measured the angle between forearm and hand axes, so a twisted wrist looked free; the
resulting pose folded the cuff on itself.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_two_hand_pose.py"
s = path.read_text(encoding="utf-8")
NL = chr(10)


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('''def elbow_of(side, wrist):
    """Elbow of the two-bone solution, below and outside the shoulder-wrist line; None when out of reach."""''',
      '''def elbow_of(side, wrist, swivel=0.0):
    """Elbow of the two-bone solution, below and outside the shoulder-wrist line, turned by swivel about that line; None when out of reach."""''')
patch('''    pole = (pole - direction * pole.dot(direction)).normalized()
    return shoulder[side] + direction * a1 + pole * h''',
      '''    pole = (pole - direction * pole.dot(direction)).normalized()
    pole = Matrix.Rotation(swivel if side == "R" else -swivel, 3, direction) @ pole
    return shoulder[side] + direction * a1 + pole * h


REST = {side: {name: bones[f"{name}.{side}"].matrix_local.to_3x3() for name in ("upper_arm", "lower_arm", "hand")} for side in "RL"}


def wrist_rotation(side, target, elbow):
    """Angle of the hand's rotation away from its rest relation to the forearm, after the two arm bones swing to the elbow and wrist."""
    upper_swing = REST[side]["upper_arm"].col[1].rotation_difference((elbow - shoulder[side]).normalized()).to_matrix()
    lower_swing = (upper_swing @ REST[side]["lower_arm"].col[1]).rotation_difference((target.translation - elbow).normalized()).to_matrix()
    carried = lower_swing @ upper_swing @ REST[side]["hand"]
    return math.degrees((carried.inverted() @ target.to_3x3()).to_quaternion().angle)''')
start = s.index("best = None")
end = s.index("if best is None:")
search = '''best = None
SWIVELS = [math.radians(a) for a in (-40, -20, 0, 20, 40)]
for gx in (-0.04, 0.0, 0.04):
    for gy in (-0.26, -0.30, -0.34, -0.38):
        for gz in (1.12, 1.19, 1.26, 1.33):
            for pitch in (20, 35, 50, 65):
                grip = Vector((gx, gy, gz))
                blade = Vector((0, -math.cos(math.radians(pitch)), math.sin(math.radians(pitch))))
                for step in range(72):
                    right = sword_world(grip, blade, math.radians(step * 5)) @ sword_relative.inverted()
                    left = left_hand(right, grip, blade)
                    # Both wrists in front of and above the belt, each on its own side or at the midline.
                    if max(right.translation.y, left.translation.y) > spine_y - args.min_wrist_forward or right.translation.x > 0.05 or left.translation.x < -0.05:
                        continue
                    if min(right.translation.z, left.translation.z) < args.min_wrist_height:
                        continue
                    choice = {}
                    for side, target in (("R", right), ("L", left)):
                        options = [(wrist_rotation(side, target, elbow), swivel) for swivel in SWIVELS if (elbow := elbow_of(side, target.translation, swivel)) is not None]
                        if options:
                            choice[side] = min(options)
                    if len(choice) < 2:
                        continue
                    bend = {side: choice[side][0] for side in "RL"}
                    score = max(bend.values()) + 0.25 * sum(bend.values())
                    if best is None or score < best[0]:
                        best = (score, grip, blade, step * 5, pitch, right, left, bend, {side: choice[side][1] for side in "RL"})
'''
s = s[:start] + search + s[end:]
patch("_, grip, blade, roll_deg, pitch, right_target, left_target, bend = best", "_, grip, blade, roll_deg, pitch, right_target, left_target, bend, swivel = best")
patch("    root, wrist, elbow = shoulder[side], target.translation, elbow_of(side, target.translation)", "    root, wrist, elbow = shoulder[side], target.translation, elbow_of(side, target.translation, swivel[side])")
patch('"wrist_bend_deg": round(bend[side], 1)}', '"wrist_rotation_deg": round(bend[side], 1), "elbow_swivel_deg": round(math.degrees(swivel[side]), 1)}')
patch("that bends both wrists least while", "that rotates both wrists least (bend and twist) while")
path.write_text(s, encoding="utf-8", newline=NL)
print("patched")
