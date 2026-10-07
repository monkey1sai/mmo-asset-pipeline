"""FK right-arm pose table (diagnostic): for a grid of contract steps on the right arm (grasp.R held, torso at rest) the sword
grip position relative to the shoulder and the blade direction, so clip keys can be chosen from reachable, natural poses."""
import json, sys, itertools
from pathlib import Path
import bpy
from mathutils import Quaternion
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_contract_pose import ContractPoser
contract_path, poses_path, out_path = sys.argv[sys.argv.index("--") + 1:][:3]
contract = json.loads(Path(contract_path).read_text(encoding="utf-8")); poses = json.loads(Path(poses_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, poses)
rows = []
# Contract vocabulary (joint-range-contract-v5 motions): shoulder flexion = upper_arm twist about right, abduction = twist about
# back, axial rotation = twist about the upper_arm bone, elbow flexion = lower_arm twist about right, pronation = hand twist about
# the lower_arm bone, wrist flexion/extension = hand swing palmar/dorsal.
for flex, abd, axial, elbow, pron, wrist in itertools.product((0, 30, 60, 90, 120, 150), (0, 30, 60, 90), (-60, -30, 0, 30, 60), (0, 45, 90, 135), (-60, -30, 0, 30, 60), (-40, 0, 40)):
    poser.reset()
    for bone, q in poses["grasp.R"].items():
        arm.pose.bones[bone].rotation_quaternion = Quaternion(q)
    bpy.context.view_layer.update()
    for step in ({"bone": "upper_arm.R", "kind": "twist", "about": "right", "degrees": flex}, {"bone": "upper_arm.R", "kind": "twist", "about": "back", "degrees": abd},
                 {"bone": "upper_arm.R", "kind": "twist", "about_bone": "upper_arm.R", "degrees": axial}, {"bone": "lower_arm.R", "kind": "twist", "about": "right", "degrees": elbow},
                 {"bone": "hand.R", "kind": "twist", "about_bone": "lower_arm.R", "degrees": pron}, {"bone": "hand.R", "kind": "swing", "toward": "palmar", "degrees": wrist}):
        if step["degrees"] == 0:
            continue
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(step, "R", 1.0)
    bpy.context.view_layer.update()
    sw = arm.pose.bones["sword"]; sh = arm.pose.bones["upper_arm.R"].head; head = arm.pose.bones["head"].head
    grip = sw.head; blade = (sw.tail - sw.head).normalized()
    rows.append({"flex": flex, "abd": abd, "axial": axial, "elbow": elbow, "pron": pron, "wrist": wrist, "grip_rel_shoulder": [round(c, 3) for c in (grip - sh)],
                 "grip": [round(c, 3) for c in grip], "blade": [round(c, 3) for c in blade], "grip_to_head_m": round((grip - head).length, 3),
                 "elbow_pos": [round(c, 3) for c in arm.pose.bones["lower_arm.R"].head]})
Path(out_path).write_text(json.dumps(rows) + chr(10), encoding="utf-8")
print("CV1_ARM_POSE_PROBE", len(rows))
