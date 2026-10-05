"""Split the cuff between a static carrier and a twist carrier.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-twist-carrier-used.py
Turning the whole cuff with the wrist made its far end sweep through the bracer it overlaps. The far cuff now
stays on wrist_transition.<side> (follows the forearm exactly); the 50 mm next to the wrist goes to
wrist_transition.<side>_twist, which poses and clips may turn by a share of the hand's twist. Only the 118
authorized cuff vertices change weights, as before. Unposed, the two carriers move identically.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:60])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_v001_assemble.py", [
    ('''for side in ("R", "L"):
    carrier = eb.get(f"wrist_transition.{side}") or eb.new(f"wrist_transition.{side}")
    forearm_bone = eb[f"lower_arm.{side}"]''',
     '''for side, suffix in (("R", ""), ("L", ""), ("R", "_twist"), ("L", "_twist")):
    carrier = eb.get(f"wrist_transition.{side}{suffix}") or eb.new(f"wrist_transition.{side}{suffix}")
    forearm_bone = eb[f"lower_arm.{side}"]'''),
    ('''        forearm_group = obj.vertex_groups.get(f"wrist_transition.{side}") or obj.vertex_groups.new(name=f"wrist_transition.{side}")
        for index, axial in enumerate(axial0):
            if axial < 0:
                t = max(0.0, 1.0 + axial / span)
                keep = t * t * (3 - 2 * t)
                hand_group.add([index], keep, "REPLACE")
                forearm_group.add([index], 1 - keep, "REPLACE")''',
     '''        forearm_group = obj.vertex_groups.get(f"wrist_transition.{side}") or obj.vertex_groups.new(name=f"wrist_transition.{side}")
        twist_group = obj.vertex_groups.get(f"wrist_transition.{side}_twist") or obj.vertex_groups.new(name=f"wrist_transition.{side}_twist")
        for index, axial in enumerate(axial0):
            if axial < 0:
                t = max(0.0, 1.0 + axial / span)
                keep = t * t * (3 - 2 * t)
                # Beyond the hand blend the cuff belongs to the twist carrier, fading to the static carrier 20 mm further back.
                u = min(1.0, max(0.0, (axial + span) / 0.02 + 1.0))
                turning = u * u * (3 - 2 * u)
                for group, weight in ((hand_group, keep), (twist_group, (1 - keep) * turning), (forearm_group, (1 - keep) * (1 - turning))):
                    if weight > 1e-6:
                        group.add([index], weight, "REPLACE")
                    else:
                        group.remove([index])'''),
    ('"cuff_carriers": ["wrist_transition.R", "wrist_transition.L"],', '"cuff_carriers": ["wrist_transition.R", "wrist_transition.L", "wrist_transition.R_twist", "wrist_transition.L_twist"],'),
])
patch("scripts/cv1_two_hand_pose.py", [
    ('    carrier = arm.pose.bones[f"wrist_transition.{side}"]', '    carrier = arm.pose.bones[f"wrist_transition.{side}_twist"]'),
    ('for side in "RL" for name in ("hand", "wrist_transition")})',
     'for side in "RL" for name in ("hand",)})' + NL + 'pose.update({f"wrist_transition.{side}_twist": list(arm.pose.bones[f"wrist_transition.{side}_twist"].rotation_quaternion) for side in "RL"})'),
])
patch("scripts/cv1_hand_correctives.py", [
    ('PARENT_GROUP["hand.R"] = "wrist_transition.R"  # the cuff is carried by this bone, not by the forearm itself',
     'PARENT_GROUP["hand.R"] = "wrist_transition.R_twist"  # the cuff next to the wrist is carried by this bone, not by the forearm itself'),
])
print("patched")
