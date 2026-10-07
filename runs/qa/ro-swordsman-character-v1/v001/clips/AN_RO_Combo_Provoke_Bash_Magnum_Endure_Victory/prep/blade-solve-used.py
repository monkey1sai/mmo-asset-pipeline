"""For each sword key outside the guard span: the reachable blade direction (wrist bend <= 40 deg over roll and swivel) closest to the intended one, with a small penalty on roll jumps between keys. Writes a JSON the spec generator reads back."""
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
GUARD = set(range(135, 249))
def fib(n):
    pts = []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n; r = math.sqrt(1 - z * z); a = math.pi * (3 - math.sqrt(5)) * i
        pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    return pts
DIRS = fib(400)
prev_roll = None
for f, _ in sw["grip"]["keys"]:
    pose(f)
    grip, want = wvec(sw["grip"], f), wvec(sw["blade"], f).normalized()
    cur_roll, cur_sw = wave(sw["roll_deg"], f), wave(sw["swivel_deg"], f)
    if f in GUARD:
        out.append({"frame": f, "guard": True, "blade": list(want), "roll": cur_roll, "swivel": cur_sw}); prev_roll = cur_roll; continue
    best = None
    for d in DIRS:
        ang = math.degrees(math.acos(max(-1.0, min(1.0, d.dot(want)))))
        if best is not None and ang > best[0] + 1e-9: continue
        for r in range(0, 360, 15):
            target = ik.hand_for_sword(sword_world(grip, d, math.radians(r)))
            b = ik.best_swivel("R", target)
            if b is None or b[0] > 40.0: continue
            droll = 0.0 if prev_roll is None else min(abs(r - prev_roll) % 360, 360 - abs(r - prev_roll) % 360)
            cand = (ang + 0.15 * droll, ang, round(b[0], 2), r, b[1], [round(c, 4) for c in d])
            if best is None or cand < best: best = cand
    if best is None:
        out.append({"frame": f, "unreachable_under_40": True, "blade": list(want), "roll": cur_roll, "swivel": cur_sw})
    else:
        out.append({"frame": f, "want": [round(c, 4) for c in want], "blade": best[5], "angle_from_want_deg": round(best[1], 1), "wrist_bend_deg": best[2], "roll": best[3], "swivel": best[4]})
        prev_roll = best[3]
Path(out_path).write_text(json.dumps(out, indent=1) + chr(10), encoding="utf-8")
print("CV1_BLADE_SOLVE " + json.dumps([(o["frame"], o.get("angle_from_want_deg"), o.get("wrist_bend_deg"), o.get("roll"), o.get("swivel")) for o in out]))
