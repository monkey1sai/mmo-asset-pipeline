"""Diagnostic (report only): least wrist bend of the right hand holding the sword with the verified r010 grip, over
roll about the blade (0-355 by 5) and elbow swivel (-60..60 by 10), for candidate grip points and blade directions,
with the rest torso (standing). Bend is the hand's rotation away from the forearm-carried rest relation (twist included)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
bpy.context.view_layer.update()
ik = ArmIK(arm)
grips = {"hip_side": (-0.35, 0.00, 0.85), "side_back": (-0.45, 0.12, 0.85), "side_front": (-0.40, -0.15, 0.85), "low_side": (-0.40, 0.05, 0.70)}
blades = {"down": (0, 0, -1), "down_forward": (0, -0.5, -0.87), "forward_down45": (0, -0.71, -0.71), "forward": (0, -1, 0),
          "outward": (-1, 0, 0), "down_back": (0, 0.3, -0.95), "idle": (-0.587, -0.492, 0.643)}
rows = []
for gname, g in grips.items():
    for bname, b in blades.items():
        best = None
        for roll in range(0, 360, 5):
            target = ik.hand_for_sword(sword_world(Vector(g), Vector(b), math.radians(roll)))
            option = ik.best_swivel("R", target)
            if option and (best is None or option[0] < best[0]):
                elbow = ik.elbow_of("R", target.translation, math.radians(option[1]))
                best = (option[0], roll, option[1], math.degrees((ik.shoulder("R") - elbow).angle(target.translation - elbow)))
        rows.append({"grip": gname, "blade": bname, "reachable": best is not None, **({"wrist_bend_deg": round(best[0], 1), "roll": best[1], "swivel": best[2], "elbow_deg": round(best[3], 1)} if best else {})})
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(rows, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
for r in rows:
    print("SCAN %-10s %-15s %s" % (r["grip"], r["blade"], ("bend %5.1f roll %3d swivel %4d elbow %5.1f" % (r["wrist_bend_deg"], r["roll"], r["swivel"], r["elbow_deg"])) if r["reachable"] else "out of reach"))
