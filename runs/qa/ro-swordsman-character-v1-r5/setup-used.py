"""Create request version ro-swordsman-character-v1-r5 from the frozen r4 request: armour contacts are judged by penetration depth.

Run from the repo root, one stage at a time:
  python -B runs/qa/ro-swordsman-character-v1-r5/setup-used.py draft      # new draft request + calibration contract
  python -B runs/qa/ro-swordsman-character-v1-r5/setup-used.py bind       # final contract with baseline ceilings, bound by hash
  python -B runs/qa/ro-swordsman-character-v1-r5/setup-used.py freeze <turn_start_utc>
  python -B runs/qa/ro-swordsman-character-v1-r5/setup-used.py baseline <started_utc> <ended_utc> <elapsed_seconds>
Authority: user, 2026-10-05, "肩甲用做法 1，另立 r5 改量穿入深度。繼續第一個候選". Armour contacts judged by depth as authorized; r4 files are not modified
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

V1 = "runs/qa/ro-swordsman-character-v1-r4"
R2 = "runs/qa/ro-swordsman-character-v1-r5"
STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"  # reused: same frozen arm pose
PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r4.json"
NEW_REQUEST = "requests/ro-swordsman-character-v1-r5.json"
OLD = ROOT / PREVIOUS_REQUEST
NEW = ROOT / NEW_REQUEST
AUTH = "肩甲用做法 1，另立 r5 改量穿入深度。繼續第一個候選"
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
    d["id"] = "ro-swordsman-character-v1-r5"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r5"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r5.json#brief; previous version r4; docs/handoffs/claude-code-character-animation-v1-20261005.md"
    envelope = d["support_envelope"]
    envelope["armor_contact"] = {
        "meshes": ["SM_RO_pauldron.L", "SM_RO_pauldron.R", "SM_RO_cuirass", "SM_RO_bracer.L", "SM_RO_bracer.R"],
        "bones": ["pauldron.L", "pauldron.R"],
        "slack_mm": 2,
        "definition": "盔甲接觸＝至少一個三角形屬於盔甲件（上列網格），或屬於被盔甲骨帶動的身體部位（三個頂點的盔甲骨權重皆>=0.5）的非手區穿插對；"
                      "盔甲件之間（例如肩甲邊緣與胸甲）也算。深度＝兩個三角形互相穿過對方平面的較淺一側距離，取兩者較小值，與法線方向無關。"
                      "每個三角形的靜止深度＝它在靜止姿勢所有盔甲接觸中的最大深度（無接觸為0）。姿勢中每個盔甲接觸的深度不得超過兩個三角形靜止深度的較大者＋2mm。",
        "reason": "盔甲件靜止時就嵌在身體網格與胸甲裡；盔甲一動，嵌入的接觸會重新洗牌，被三角形對數當成新穿插。改量深度只看接觸是否變深。",
    }
    gates = envelope["joint_range_gates"]
    gates["armor_contact"] = "盔甲接觸改以深度判定：每個盔甲接觸不得比相關三角形的靜止深度深2mm以上；典型與極端角度皆適用。"
    gates["body_ratchet"] += " r5起，盔甲接觸不計入對數上限，改由 armor_contact 判定；其餘身體穿插仍照基準同動作的對數上限。"
    envelope.pop("joint_range_contract", None)
    envelope.pop("calibration", None)
    d["assumptions"].append("r5 與 r4 的差異僅一項：涉及盔甲件（含被盔甲骨帶動的身體部位）的穿插改量深度（不得比靜止時深2mm以上），其餘身體穿插的對數上限、手區零穿插、塌陷、邊長比門檻皆同。候選次數與時間延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art(PREVIOUS_REQUEST), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(V1 + "/quality-ledger.json"), "freeze": art(V1 + "/freeze.json"), "earlier_version": old["phase_history"]["previous_version"],
                                              "reason": "移動肩甲後新增的接觸多為靜止時已嵌入的盔甲接觸重新洗牌，對數上限無法分辨，見 runs/qa/ro-swordsman-character-v1/v001/v001-pause-07.json", "authority": AUTH,
                                              "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選）",
                                              "quality_targets_lowered": False,
                                              "thresholds_changed": "盔甲接觸由對數上限改為深度上限（靜止深度＋2mm）"}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "budget", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate", "holdout_policy"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["quality"].items() if k != "status"}, {k: v for k, v in d["quality"].items() if k != "status"})
    assert same(old["support_envelope"]["joint_ranges_deg"], envelope["joint_ranges_deg"]) and same(old["support_envelope"]["frozen_poses"], envelope["frozen_poses"])
    dump(NEW_REQUEST, d)
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v6-calibration.json"], check=True, cwd=ROOT)
    record_path = "runs/qa/ro-swordsman-character-v1/authorizations.json"
    record = json.loads((ROOT / record_path).read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "text": AUTH,
                              "covers": ["肩甲做法1：綁定身體網格上的重複肩甲、肩甲上緣轉軸、輔助骨跟隨", "另立 ro-swordsman-character-v1-r5：盔甲接觸改量穿入深度（靜止深度＋2mm），重新登記baseline", "第一個候選延續"],
                              "interpretation": "盔甲接觸包含盔甲件之間（肩甲邊緣與胸甲）及被盔甲骨帶動的身體部位；這是上一則回報所述『肩甲邊緣嵌進胸甲』與『綁過去的那層盔甲』兩類接觸。",
                              "not_covered": ["其他門檻的任何放寬", "衣擺等非盔甲部位的門檻", "保護區C", "commit／push"]})
    record["applies_to"].append("ro-swordsman-character-v1-r5")
    dump(record_path, record, mode="w")
    print("draft written", workbench.validate_request(d))

elif stage == "bind":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    calibration = R2 + "/baseline-joint-range-v6-calibration/joint-range-result.json"
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v6.json", calibration], check=True, cwd=ROOT)
    d["support_envelope"]["joint_range_contract"] = art(R2 + "/joint-range-contract-v6.json")
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
    dump(V1 + "/closure.json", {"closed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "request": "ro-swordsman-character-v1-r4",
                                "result": "superseded before any candidate was recorded", "reason": "Moving the pauldrons reshuffles armour contacts embedded at rest, which the count-based body ratchet cannot tell from new penetration.",
                                "evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-07.json", "successor": NEW_REQUEST,
                                "ledger_trials": ["baseline"], "candidates_recorded": 0, "candidate_in_progress_carried_over": "v001", "files_kept_unchanged": True, "authority": AUTH})
    print("frozen", workbench.request_sha256(d))

elif stage == "baseline":
    started, ended, elapsed = sys.argv[2], sys.argv[3], float(sys.argv[4])
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "specified" and d["quality"]["status"] == "frozen"
    previous = json.loads((ROOT / V1 / "quality-ledger.json").read_text(encoding="utf-8"))["trials"][0]
    joints_path = R2 + "/baseline-joint-range-v6/joint-range-result.json"
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
