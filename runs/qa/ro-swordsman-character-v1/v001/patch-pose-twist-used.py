"""Two-hand pose: the cuff carrier bones take a share of the hand's twist about the forearm.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-pose-twist-used.py
Without a forearm twist bone the whole twist lands in the 30 mm wrist blend and the cuff folds on itself.
wrist_transition already carries the cuff and follows the forearm; turning it by part of the hand's twist is
ordinary pose data, baked into the pose like any other bone rotation.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_two_hand_pose.py"
s = path.read_text(encoding="utf-8")
NL = chr(10)


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--min-wrist-height", type=float, default=1.15)',
      'parser.add_argument("--twist-share", type=float, default=0.5, help="share of the hand twist about the forearm taken by the cuff carrier bone")' + NL
      + 'parser.add_argument("--min-wrist-height", type=float, default=1.15)')
patch('''    hand.matrix = target
    hand.location = (0, 0, 0)
    bpy.context.view_layer.update()''',
      '''    # Twist of the hand about the forearm, measured from where the hand would sit if it only followed the forearm.
    forearm = (wrist - elbow).normalized()
    relative = (target.to_3x3() @ hand.matrix.to_3x3().inverted()).to_quaternion()
    twist = 2 * math.atan2(Vector((relative.x, relative.y, relative.z)).dot(forearm), relative.w)
    twist = (twist + math.pi) % (2 * math.pi) - math.pi
    carrier = arm.pose.bones[f"wrist_transition.{side}"]
    carrier.matrix = Matrix.Translation(carrier.matrix.translation) @ (Matrix.Rotation(twist * args.twist_share, 3, forearm) @ carrier.matrix.to_3x3()).to_4x4()
    carrier.location = (0, 0, 0)
    bpy.context.view_layer.update()
    hand.matrix = target
    hand.location = (0, 0, 0)
    bpy.context.view_layer.update()''')
patch('"wrist_rotation_deg": round(bend[side], 1),', '"wrist_rotation_deg": round(bend[side], 1), "twist_about_forearm_deg": round(math.degrees(twist), 1), "twist_share_on_cuff_carrier": args.twist_share,')
patch('pose.update({f"hand.{side}": list(arm.pose.bones[f"hand.{side}"].rotation_quaternion) for side in "RL"})',
      'pose.update({f"{name}.{side}": list(arm.pose.bones[f"{name}.{side}"].rotation_quaternion) for side in "RL" for name in ("hand", "wrist_transition")})')
path.write_text(s, encoding="utf-8", newline=NL)
print("patched")
