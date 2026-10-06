"""Create request version ro-swordsman-character-v1-r2 from the frozen v1 request: pose definitions only.

Run from the repo root, one stage at a time:
  python -B runs/qa/ro-swordsman-character-v1-r2/setup-used.py draft      # new draft request + calibration contract
  python -B runs/qa/ro-swordsman-character-v1-r2/setup-used.py bind       # final contract with baseline ceilings, bound by hash
  python -B runs/qa/ro-swordsman-character-v1-r2/setup-used.py freeze <turn_start_utc>
  python -B runs/qa/ro-swordsman-character-v1-r2/setup-used.py baseline <started_utc> <ended_utc> <elapsed_seconds>
Authority: user, 2026-10-05, "袖口權重授權；契約用做法 1。繼續第一個候選". No threshold changes; v1 files are not modified
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

V1 = "runs/qa/ro-swordsman-character-v1"
R2 = "runs/qa/ro-swordsman-character-v1-r2"
OLD = ROOT / "requests/ro-swordsman-character-v1.json"
NEW = ROOT / "requests/ro-swordsman-character-v1-r2.json"
AUTH = "袖口權重授權；契約用做法 1。繼續第一個候選"
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
    d["id"] = "ro-swordsman-character-v1-r2"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r2"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r2.json#brief; requests/ro-swordsman-character-v1.json; docs/handoffs/claude-code-character-animation-v1-20261005.md"
    envelope = d["support_envelope"]
    envelope["combination_poses"] = ["抬臂過頭（雙臂保持平行）", "雙手下劈（需要候選的雙手握劍姿勢 two_hand_chop）", "深蹲／落地", "空手握拳（不得出現劍柄壓痕）", "張掌施法（左手）",
                                     "握劍＋腕屈伸／橈尺偏（需要候選的FK握姿 grasp.R）", "仰臥睡姿（於睡眠clip評估）"]
    envelope["pose_definition"] = ("肩、肘、髖、膝以繞身體軸旋轉定義：屈伸繞左右軸、外展繞前後軸。v1的『朝某方向擺動』在超過90度後會使肢體越過中線，"
                                   "抬臂過頭變成雙臂交叉、雙手下劈使雙手重疊，任何候選都無法通過；r2只修正這些定義，角度與所有門檻不變。")
    envelope.pop("joint_range_contract", None)
    envelope.pop("calibration", None)
    d["assumptions"].append("r2 與 v1 的差異僅限姿勢定義（肩肘髖膝的旋轉軸、抬臂過頭、雙手下劈需候選姿勢）；角度、門檻、動作清單、品質契約、預算與保護區規則皆同 v1。候選次數與時間自 v1 延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art("requests/ro-swordsman-character-v1.json"), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(V1 + "/quality-ledger.json"), "freeze": art(V1 + "/freeze.json"),
                                              "reason": "凍結契約的姿勢定義缺陷，見 " + V1 + "/v001/v001-pause-01.json", "authority": AUTH,
                                              "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選）",
                                              "quality_targets_lowered": False, "thresholds_changed": False}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "budget", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate", "holdout_policy"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["quality"].items() if k != "status"}, {k: v for k, v in d["quality"].items() if k != "status"})
    assert same(old["support_envelope"]["joint_ranges_deg"], envelope["joint_ranges_deg"]) and same(old["support_envelope"]["joint_range_gates"], envelope["joint_range_gates"])
    dump("requests/ro-swordsman-character-v1-r2.json", d)
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", "requests/ro-swordsman-character-v1-r2.json", R2 + "/joint-range-contract-v3-calibration.json"], check=True, cwd=ROOT)
    record = json.loads((ROOT / V1 / "authorizations.json").read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "text": AUTH,
                              "covers": ["保護區：r010右手腕關節後118個頂點的權重改為在30mm內由手掌漸變到前臂，左手同樣處理；其餘786個頂點維持凍結",
                                         "契約做法1：另立需求版本 ro-swordsman-character-v1-r2，只修正姿勢定義，門檻不變，重新登記baseline", "第一個候選延續，次數與時間照算"],
                              "not_covered": ["保護區C（輔助骨）", "r010右手其餘頂點的權重、Basis、拓樸", "手肘135度門檻的任何放寬", "commit／push"]})
    record["protected_zone"]["D_cuff_weights"] = "authorized"
    record["applies_to"] = ["ro-swordsman-character-v1", "ro-swordsman-character-v1-r2"]
    dump(V1 + "/authorizations.json", record, mode="w")
    print("draft written", workbench.validate_request(d))

elif stage == "bind":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    calibration = R2 + "/baseline-joint-range-v3-calibration/joint-range-result.json"
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", "requests/ro-swordsman-character-v1-r2.json", R2 + "/joint-range-contract-v3.json", calibration], check=True, cwd=ROOT)
    d["support_envelope"]["joint_range_contract"] = art(R2 + "/joint-range-contract-v3.json")
    d["support_envelope"]["calibration"] = {"result": calibration, "sha256": sha(calibration), "note": "基準角色以v3姿勢定義實跑，只用來記錄防退步上限；角度未調整。"}
    dump("requests/ro-swordsman-character-v1-r2.json", d, mode="w")
    print("bound", d["support_envelope"]["joint_range_contract"]["sha256"][:16])

elif stage == "freeze":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "draft" and not d["open_questions"]
    d["status"], d["quality"]["status"] = "specified", "frozen"
    assert not workbench.validate_request(d) and not workbench.readiness(d)
    dump("requests/ro-swordsman-character-v1-r2.json", d, mode="w")
    contract = d["support_envelope"]["joint_range_contract"]
    assert sha(contract["path"]) == contract["sha256"]
    dump(R2 + "/freeze.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "turn_start_utc": sys.argv[2], "authority": AUTH,
                               "request": {"path": "requests/ro-swordsman-character-v1-r2.json", "file_sha256": sha("requests/ro-swordsman-character-v1-r2.json"),
                                           "request_sha256": workbench.request_sha256(d), "protocol_sha256": workbench.quality_sha256(d)},
                               "joint_range_contract": contract, "max_candidate_trials": d["production"]["max_revisions"], "budget": d["quality"]["budget"],
                               "required_checks": [c["id"] for c in workbench.required_checks(d)], "authorization_record": V1 + "/authorizations.json",
                               "rule": "The request file must not change after this point; a contract change needs a new request version and baseline."})
    dump(V1 + "/closure.json", {"closed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "request": "ro-swordsman-character-v1",
                                "result": "superseded before any candidate was recorded", "reason": "Pose definitions in the frozen joint-range contract made two combination poses impossible to pass.",
                                "evidence": V1 + "/v001/v001-pause-01.json", "successor": "requests/ro-swordsman-character-v1-r2.json",
                                "ledger_trials": ["baseline"], "candidates_recorded": 0, "candidate_in_progress_carried_over": "v001", "files_kept_unchanged": True, "authority": AUTH})
    print("frozen", workbench.request_sha256(d))

elif stage == "baseline":
    started, ended, elapsed = sys.argv[2], sys.argv[3], float(sys.argv[4])
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "specified" and d["quality"]["status"] == "frozen"
    previous = json.loads((ROOT / V1 / "quality-ledger.json").read_text(encoding="utf-8"))["trials"][0]
    joints_path = R2 + "/baseline-joint-range-v3/joint-range-result.json"
    joints = json.loads((ROOT / joints_path).read_text(encoding="utf-8"))
    failed = [r for r in joints["results"] if not r["pass"]]
    unposed = [r for r in failed if r["status"] != "measured"]
    old_joints = previous["evidence"]["checks"]["joint-range"]["artifacts"][0]["path"]
    checks = copy.deepcopy(previous["evidence"]["checks"])
    for check in checks.values():
        check["artifacts"] = [art(joints_path) if a["path"] == old_joints else a for a in check["artifacts"]]
    checks["deformation"]["method"] = f"Joint-range sweep on this file with the r2 contract: {len(failed)} of {len(joints['results'])} motions fail or cannot be posed."
    checks["joint-range"]["method"] = f"scripts/cv1_joint_range.py with the frozen r2 contract: numeric gate false, {len(failed) - len(unposed)} motions fail and {len(unposed)} cannot be posed."
    request_sha, protocol_sha = workbench.request_sha256(d), workbench.quality_sha256(d)
    evidence = {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "checks": checks,
                "deliverables": previous["evidence"]["deliverables"], "subject_artifacts": previous["evidence"]["subject_artifacts"]}
    trial = {"id": "baseline", "parent_id": None, "status": "completed", "started_utc": started, "ended_utc": ended, "elapsed_seconds": elapsed,
             "protocol_sha256": protocol_sha, "reviewer": previous["reviewer"] + "; same file, views and scores as the v1 baseline, joint-range re-measured with the r2 contract",
             "previews": previous["previews"], "scores": previous["scores"], "evidence": evidence}
    dump(R2 + "/quality-ledger.json", {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "protocol_sha256": protocol_sha,
                                       "joint_range_contract": d["support_envelope"]["joint_range_contract"], "trials": [trial],
                                       "phase_history": {"previous_ledger": art(V1 + "/quality-ledger.json"), "previous_phase_reopened": False, "quality_targets_lowered": False,
                                                         "elapsed_carried_from_previous_version_seconds": previous["elapsed_seconds"]}})
    print("baseline registered", len(failed), "of", len(joints["results"]), "fail")
