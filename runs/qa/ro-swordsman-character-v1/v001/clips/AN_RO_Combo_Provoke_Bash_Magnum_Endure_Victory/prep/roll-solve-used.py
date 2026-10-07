"""For each sword key of a spec: the roll and swivel with the least wrist bend (diagnostic; the FK pose of that frame is set first)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector, Matrix
ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
from cv1_contract_pose import ContractPoser
spec_path, contract_path, poses_path, out_path = sys.argv[sys.argv.index("--") + 1:][:4]
spec = json.loads(Path(spec_path).read_text(encoding="utf-8")); contract = json.loads(Path(contract_path).read_text(encoding="utf-8")); poses = json.loads(Path(poses_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser, ik = ContractPoser(arm, contract, poses), ArmIK(arm, contract=contract)
frames = spec["frames"]
def keyed(keys, f):
    keys = sorted(keys, key=lambda x: x[0])
    if f <= keys[0][0]: return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0); s = t * t * (3 - 2 * t)
            return [a + (b - a) * s for a, b in zip(v0, v1)] if isinstance(v0, list) else v0 + (v1 - v0) * s
    return keys[-1][1]
def wave(v, f):
    if isinstance(v, (int, float)): return float(v)
    return float(keyed(v["keys"], f)) if "keys" in v else float(v["base"])
def wvec(v, f):
    return Vector(v) if isinstance(v, list) else Vector(keyed(v["keys"], f))
AX = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
ph, pr = arm.data.bones["pelvis"].head_local.copy(), arm.data.bones["pelvis"].matrix_local.to_3x3()
def pose(f):
    poser.reset()
    for item in spec.get("poses", []):
        name, w = (item, 1.0) if isinstance(item, str) else (item["name"], wave(item["weight"], f))
        for bone, q in poses[name].items():
            arm.pose.bones[bone].rotation_quaternion = Quaternion(q) if w >= 1 else Quaternion().slerp(Quaternion(q), w)
    if spec.get("pelvis"):
        turn = Quaternion()
        for item in spec["pelvis"].get("rotation", []): turn = Quaternion(AX[item["axis"]], math.radians(wave(item["degrees"], f))) @ turn
        pb = arm.pose.bones["pelvis"]; pb.rotation_mode = "QUATERNION"
        pb.matrix = Matrix.Translation(wvec(spec["pelvis"]["location_m"], f)) @ (turn.to_matrix() @ pr).to_4x4()
    bpy.context.view_layer.update()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=wave(step["degrees"], f)), step.get("side"), 1.0)
    bpy.context.view_layer.update()
sw = spec["sword"]; out = []
for f, _ in sw["grip"]["keys"]:
    pose(f)
    grip, blade = wvec(sw["grip"], f), wvec(sw["blade"], f).normalized()
    pitch = math.radians(wave(sw.get("pitch_deg", 0.0), f))
    if pitch: blade = (Quaternion(blade.cross(Vector((0, 0, 1))).normalized(), pitch) @ blade).normalized()
    options = []
    for r in range(0, 360, 5):
        target = ik.hand_for_sword(sword_world(grip, blade, math.radians(r)))
        best = ik.best_swivel("R", target)
        if best is not None: options.append((round(best[0], 2), r, round(best[1], 1)))
    cur_roll, cur_sw = wave(sw["roll_deg"], f), wave(sw["swivel_deg"], f)
    target = ik.hand_for_sword(sword_world(grip, blade, math.radians(cur_roll)))
    elbow = ik.elbow_of("R", target.translation, math.radians(cur_sw))
    cur_bend = None if elbow is None else round(ik.wrist_bend_deg("R", target, elbow), 2)
    options.sort()
    out.append({"frame": f, "current": {"roll": cur_roll, "swivel": cur_sw, "wrist_bend_deg": cur_bend}, "best": options[:3], "under_60": [o for o in options if o[0] <= 60][:12]})
Path(out_path).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print("CV1_ROLL_SOLVE " + json.dumps([(o["frame"], o["current"]["wrist_bend_deg"], o["best"][0] if o["best"] else None) for o in out]))
