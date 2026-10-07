"""Sword bone placement of the frozen two_hand_chop pose (diagnostic): grip, blade direction and roll for sword_world."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import sword_world
poses = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
for bone, q in poses["two_hand_chop"].items():
    arm.pose.bones[bone].rotation_quaternion = Quaternion(q)
bpy.context.view_layer.update()
m = arm.pose.bones["sword"].matrix
grip, blade, xaxis = m.translation.copy(), m.col[1].to_3d().normalized(), m.col[0].to_3d().normalized()
best = min(((sword_world(grip, blade, math.radians(r)).col[0].to_3d() - xaxis).length, r) for r in [x / 10 for x in range(0, 3600)])
hand = arm.pose.bones["hand.R"].head.copy(); shoulder = arm.pose.bones["upper_arm.R"].head.copy()
print("CV1_CHOP_SWORD " + json.dumps({"grip": [round(c, 4) for c in grip], "blade": [round(c, 4) for c in blade], "roll_deg": best[1], "x_error": round(best[0], 6),
                                      "wrist": [round(c, 4) for c in hand], "shoulder": [round(c, 4) for c in shoulder], "wrist_from_shoulder_m": round((hand - shoulder).length, 4),
                                      "hand_L": [round(c, 4) for c in arm.pose.bones["hand.L"].head]}))
