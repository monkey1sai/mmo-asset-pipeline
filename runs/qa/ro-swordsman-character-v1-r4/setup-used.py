"""Create request version ro-swordsman-character-v1-r4 from the frozen r3 request: the two-hand chop's body ceilings come from the baseline in the same arm pose.

Run from the repo root, one stage at a time:
  python -B runs/qa/ro-swordsman-character-v1-r4/setup-used.py draft      # new draft request + calibration contract
  python -B runs/qa/ro-swordsman-character-v1-r4/setup-used.py bind       # final contract with baseline ceilings, bound by hash
  python -B runs/qa/ro-swordsman-character-v1-r4/setup-used.py freeze <turn_start_utc>
  python -B runs/qa/ro-swordsman-character-v1-r4/setup-used.py baseline <started_utc> <ended_utc> <elapsed_seconds>
Authority: user, 2026-10-05, "雙手下劈用做法 1。繼續第一個候選". One ceiling source changed as authorized; r3 files are not modified
except the shared authorization record (outside any request hash) and a closure note.
"""
import copy
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import workbench

V1 = "runs/qa/ro-swordsman-character-v1-r3"
R2 = "runs/qa/ro-swordsman-character-v1-r4"
STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"
PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r3.json"
NEW_REQUEST = "requests/ro-swordsman-character-v1-r4.json"
OLD = ROOT / PREVIOUS_REQUEST
NEW = ROOT / NEW_REQUEST
AUTH = "雙手下劈用做法 1。繼續第一個候選"
NL = chr(10)
stage = sys.argv[1]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def art(path):
    return {"path": path, "sha256": sha(path)}


def dump(path, payload, mode="x"):
    with open(ROOT / path, mode, encoding="utf-8", newline=NL) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2 if path.startswith("requests/") else 1)
        handle.write(NL)


if stage == "draft":
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

elif stage == "bind":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    calibration = R2 + "/baseline-joint-range-v5-calibration/joint-range-result.json"
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v5.json", calibration], check=True, cwd=ROOT)
    d["support_envelope"]["joint_range_contract"] = art(R2 + "/joint-range-contract-v5.json")
    d["support_envelope"]["calibration"] = {"result": calibration, "sha256": sha(calibration), "note": "基準角色以v3姿勢定義實跑，只用來記錄防退步上限；角度未調整。"}
    dump(NEW_REQUEST, d, mode="w")
    print("bound", d["support_envelope"]["joint_range_contract"]["sha256"][:16])

elif stage == "freeze":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "draft" and not d["open_questions"]
    d["status"], d["quality"]["status"] = "specified", "frozen"
    assert not workbench.validate_request(d) and not workbench.readiness(d)
    dump(NEW_REQUEST, d, mode="w")
    contract = d["support_envelope"]["joint_range_contract"]
    assert sha(contract["path"]) == contract["sha256"]
    dump(R2 + "/freeze.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "turn_start_utc": sys.argv[2], "authority": AUTH,
                               "request": {"path": NEW_REQUEST, "file_sha256": sha(NEW_REQUEST),
                                           "request_sha256": workbench.request_sha256(d), "protocol_sha256": workbench.quality_sha256(d)},
                               "joint_range_contract": contract, "max_candidate_trials": d["production"]["max_revisions"], "budget": d["quality"]["budget"],
                               "required_checks": [c["id"] for c in workbench.required_checks(d)], "authorization_record": "runs/qa/ro-swordsman-character-v1/authorizations.json",
                               "rule": "The request file must not change after this point; a contract change needs a new request version and baseline."})
    dump(V1 + "/closure.json", {"closed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "request": "ro-swordsman-character-v1-r3",
                                "result": "superseded before any candidate was recorded", "reason": "The two-hand chop had no baseline to compare with and fell to a body bound no arm-raising pose can meet.",
                                "evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-03.json", "successor": NEW_REQUEST,
                                "ledger_trials": ["baseline"], "candidates_recorded": 0, "candidate_in_progress_carried_over": "v001", "files_kept_unchanged": True, "authority": AUTH})
    print("frozen", workbench.request_sha256(d))

elif stage == "baseline":
    started, ended, elapsed = sys.argv[2], sys.argv[3], float(sys.argv[4])
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "specified" and d["quality"]["status"] == "frozen"
    previous = json.loads((ROOT / V1 / "quality-ledger.json").read_text(encoding="utf-8"))["trials"][0]
    joints_path = R2 + "/baseline-joint-range-v5/joint-range-result.json"
    joints = json.loads((ROOT / joints_path).read_text(encoding="utf-8"))
    failed = [r for r in joints["results"] if not r["pass"]]
    unposed = [r for r in failed if r["status"] != "measured"]
    old_joints = previous["evidence"]["checks"]["joint-range"]["artifacts"][0]["path"]
    checks = copy.deepcopy(previous["evidence"]["checks"])
    for check in checks.values():
        check["artifacts"] = [art(joints_path) if a["path"] == old_joints else a for a in check["artifacts"]]
    checks["deformation"]["method"] = f"Joint-range sweep on this file with the r4 contract: {len(failed)} of {len(joints['results'])} motions fail or cannot be posed."
    checks["joint-range"]["method"] = f"scripts/cv1_joint_range.py with the frozen r4 contract: numeric gate false, {len(failed) - len(unposed)} motions fail and {len(unposed)} cannot be posed."
    request_sha, protocol_sha = workbench.request_sha256(d), workbench.quality_sha256(d)
    evidence = {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "checks": checks,
                "deliverables": previous["evidence"]["deliverables"], "subject_artifacts": previous["evidence"]["subject_artifacts"]}
    trial = {"id": "baseline", "parent_id": None, "status": "completed", "started_utc": started, "ended_utc": ended, "elapsed_seconds": elapsed,
             "protocol_sha256": protocol_sha, "reviewer": previous["reviewer"] + "; same file, views and scores as the v1 baseline, joint-range re-measured with the r4 contract",
             "previews": previous["previews"], "scores": previous["scores"], "evidence": evidence}
    dump(R2 + "/quality-ledger.json", {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "protocol_sha256": protocol_sha,
                                       "joint_range_contract": d["support_envelope"]["joint_range_contract"], "trials": [trial],
                                       "phase_history": {"previous_ledger": art(V1 + "/quality-ledger.json"), "previous_phase_reopened": False, "quality_targets_lowered": False,
                                                         "elapsed_carried_from_previous_version_seconds": previous["elapsed_seconds"]}})
    print("baseline registered", len(failed), "of", len(joints["results"]), "fail")
