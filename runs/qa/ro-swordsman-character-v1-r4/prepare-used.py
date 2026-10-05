"""Prepare request version r4: the two-hand chop's body ceilings come from the baseline in the same arm pose.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1-r4/prepare-used.py
Authority: user, 2026-10-05, "雙手下劈用做法 1。繼續第一個候選".
Writes the baseline pose stub (arm rotations only), patches the joint-range tool to enforce frozen poses, and
derives the r4 setup script from the r3 one.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NL = chr(10)
POSES = "assets/processed/ro-swordsman-character-v1/v001/a29-pose/poses.json"
STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"


def patch(text, old, new):
    assert text.count(old) == 1, old[:70]
    return text.replace(old, new)


# 1. baseline stub: the candidate pose's arm rotations only (the baseline has no matching hand or finger frames)
poses = json.loads((ROOT / POSES).read_text(encoding="utf-8"))
arms = poses["two_hand_chop_arms"]
assert sorted(arms) == ["lower_arm.L", "lower_arm.R", "upper_arm.L", "upper_arm.R"] and all(poses["two_hand_chop"][k] == v for k, v in arms.items())
with open(ROOT / STUB, "x", encoding="utf-8", newline=NL) as handle:
    json.dump({"two_hand_chop": arms, "source": {"path": POSES, "sha256": hashlib.sha256((ROOT / POSES).read_bytes()).hexdigest()},
               "note": "Arm bone rotations of the candidate's two-hand grip pose; used to pose the baseline for the body ratchet only."}, handle, indent=1)
    handle.write(NL)

# 2. joint-range tool: a pose the request froze must be used as frozen
path = ROOT / "scripts/cv1_joint_range.py"
s = path.read_text(encoding="utf-8")
s = patch(s, '''rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8")) if args.rules else None
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8")) if args.poses else {}''',
          '''rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8")) if args.rules else None
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8")) if args.poses else {}
if args.request:
    # Arm rotations the request froze for a candidate-supplied pose must be used exactly; the body ceilings were measured with them.
    for pose_name, frozen in request["support_envelope"].get("frozen_poses", {}).items():
        for bone_name, quaternion in frozen["arm_rotations"].items():
            given = poses.get(pose_name, {}).get(bone_name)
            if pose_name in poses and (given is None or max(abs(a - b) for a, b in zip(given, quaternion)) > 1e-9):
                raise SystemExit(f"FROZEN_POSE_MISMATCH {pose_name} {bone_name}")''')
path.write_text(s, encoding="utf-8", newline=NL)

# 3. r4 setup script, derived from the r3 one
src = (ROOT / "runs/qa/ro-swordsman-character-v1-r3/setup-used.py").read_text(encoding="utf-8")
start, end = src.index('if stage == "draft":'), src.index('elif stage == "bind":')
draft = '''if stage == "draft":
    old = json.loads(OLD.read_text(encoding="utf-8"))
    d = copy.deepcopy(old)
    d["id"] = "ro-swordsman-character-v1-r4"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r4"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r4.json#brief; previous version r3; docs/handoffs/claude-code-character-animation-v1-20261005.md"
    envelope = d["support_envelope"]
    envelope["joint_range_gates"]["body_ratchet"] += " 需要候選姿勢的動作（雙手下劈）：手臂旋轉於本需求以雜湊凍結，基準以同一組手臂旋轉擺姿量出上限；候選必須使用凍結的手臂旋轉，否則量測中止。"
    stub = json.loads((ROOT / STUB).read_text(encoding="utf-8"))
    envelope["frozen_poses"] = {"two_hand_chop": {"arm_rotations": stub["two_hand_chop"], "candidate_pose": stub["source"], "baseline_stub": art(STUB),
                                                   "note": "手與手指的旋轉屬候選資料，不在凍結範圍；手區零交叉的要求不變。"}}
    envelope.pop("joint_range_contract", None)
    envelope.pop("calibration", None)
    d["assumptions"].append("r4 與 r3 的差異僅一項：雙手下劈的身體防退步上限改由基準以同一組手臂旋轉量得，手臂旋轉以雜湊凍結。其餘角度、門檻、動作清單、品質契約、預算與保護區規則皆同。候選次數與時間延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art(PREVIOUS_REQUEST), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(V1 + "/quality-ledger.json"), "freeze": art(V1 + "/freeze.json"), "earlier_version": old["phase_history"]["previous_version"],
                                              "reason": "雙手下劈的身體上限無基準可比，見 runs/qa/ro-swordsman-character-v1/v001/v001-pause-03.json", "authority": AUTH,
                                              "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選）",
                                              "quality_targets_lowered": False,
                                              "thresholds_changed": "雙手下劈的身體上限由一般上限（0對、邊長比3）改為基準同手臂姿勢的實測值"}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "budget", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate", "holdout_policy"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["quality"].items() if k != "status"}, {k: v for k, v in d["quality"].items() if k != "status"})
    assert same(old["support_envelope"]["joint_ranges_deg"], envelope["joint_ranges_deg"])
    dump(NEW_REQUEST, d)
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v5-calibration.json"], check=True, cwd=ROOT)
    record_path = "runs/qa/ro-swordsman-character-v1/authorizations.json"
    record = json.loads((ROOT / record_path).read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "text": AUTH,
                              "covers": ["雙手下劈做法1：另立 ro-swordsman-character-v1-r4 並重新登記baseline", "雙手握劍姿勢的手臂旋轉以雜湊凍結，基準以同姿勢量出身體上限", "第一個候選延續"],
                              "not_covered": ["其他門檻的任何放寬", "契約修正先做後報的常設授權（使用者未回覆，維持每次先問）", "保護區C", "commit／push"]})
    record["applies_to"].append("ro-swordsman-character-v1-r4")
    dump(record_path, record, mode="w")
    print("draft written", workbench.validate_request(d))

'''
src = src[:start] + draft + src[end:]
src = patch(src, 'V1 = "runs/qa/ro-swordsman-character-v1-r2"', 'V1 = "runs/qa/ro-swordsman-character-v1-r3"')
src = patch(src, 'R2 = "runs/qa/ro-swordsman-character-v1-r3"', 'R2 = "runs/qa/ro-swordsman-character-v1-r4"' + NL + 'STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"')
src = patch(src, 'PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r2.json"', 'PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r3.json"')
src = patch(src, 'NEW_REQUEST = "requests/ro-swordsman-character-v1-r3.json"', 'NEW_REQUEST = "requests/ro-swordsman-character-v1-r4.json"')
src = patch(src, 'AUTH = "契約用做法 1。繼續第一個候選"', 'AUTH = "雙手下劈用做法 1。繼續第一個候選"')
src = src.replace("joint-range-contract-v4", "joint-range-contract-v5").replace("baseline-joint-range-v4", "baseline-joint-range-v5")
src = src.replace('"request": "ro-swordsman-character-v1-r2",', '"request": "ro-swordsman-character-v1-r3",').replace("r3 contract", "r4 contract")
src = src.replace('"evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-02.json"', '"evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-03.json"')
src = src.replace("Two gates could not be passed by any candidate: toe ceilings taken from a non-deforming baseline, and the hand rule at the extreme of a side bend.",
                  "The two-hand chop had no baseline to compare with and fell to a body bound no arm-raising pose can meet.")
src = src.replace("Create request version ro-swordsman-character-v1-r3 from the frozen r2 request: two infeasible gates corrected.",
                  "Create request version ro-swordsman-character-v1-r4 from the frozen r3 request: the two-hand chop's body ceilings come from the baseline in the same arm pose.")
src = src.replace("runs/qa/ro-swordsman-character-v1-r3/setup-used.py", "runs/qa/ro-swordsman-character-v1-r4/setup-used.py")
src = src.replace('Authority: user, 2026-10-05, "契約用做法 1。繼續第一個候選". Two gate changes as authorized; r2 files are not modified',
                  'Authority: user, 2026-10-05, "雙手下劈用做法 1。繼續第一個候選". One ceiling source changed as authorized; r3 files are not modified')
with open(ROOT / "runs/qa/ro-swordsman-character-v1-r4/setup-used.py", "x", encoding="utf-8", newline=NL) as handle:
    handle.write(src)
print("prepared")
