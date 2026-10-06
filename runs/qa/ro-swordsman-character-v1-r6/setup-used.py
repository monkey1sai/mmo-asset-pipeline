"""Create request version ro-swordsman-character-v1-r6 from the frozen r4 request: only the per-candidate trial cap changes.

Run from the repo root, one stage at a time:
  python -B runs/qa/ro-swordsman-character-v1-r6/setup-used.py draft      # new draft request + authorization entry
  python -B runs/qa/ro-swordsman-character-v1-r6/setup-used.py freeze <turn_start_utc>
  python -B runs/qa/ro-swordsman-character-v1-r6/setup-used.py baseline <started_utc> <ended_utc> <elapsed_seconds>
Authority: user, 2026-10-05, "預算用做法 1（另立 r6，每候選 18 小時）；扭轉骨用做法 1".
The joint-range contract, calibration and frozen poses are unchanged, so the r4 baseline measurement is carried over
without re-measuring. r4 files are not modified except a closure note; the shared authorization record is outside any
request hash. The r5 draft was withdrawn before freezing and is skipped.
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

PREV_DIR = "runs/qa/ro-swordsman-character-v1-r4"
NEW_DIR = "runs/qa/ro-swordsman-character-v1-r6"
PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r4.json"
NEW_REQUEST = "requests/ro-swordsman-character-v1-r6.json"
OLD = ROOT / PREVIOUS_REQUEST
NEW = ROOT / NEW_REQUEST
AUTH = "預算用做法 1（另立 r6，每候選 18 小時）；扭轉骨用做法 1"
TRIAL_SECONDS = 64800
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
    d["id"] = "ro-swordsman-character-v1-r6"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r6"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r6.json#brief; previous version r4 (r5 withdrawn before freezing); docs/handoffs/claude-code-character-animation-v1-20261005.md"
    d["budget"]["trial_seconds"] = TRIAL_SECONDS
    d["quality"]["budget"]["trial_seconds"] = TRIAL_SECONDS
    d["budget"]["basis"] += " r6：P2到P5屬同一候選的生命週期，6小時不足以完成P3到P5（獨立計畫審查 runs/qa/ro-swordsman-character-v1/v001/p3-plan-review-01.md），使用者授權每候選上限改為64,800秒（18小時）；候選數4與總上限172,800秒不變。"
    d["assumptions"].append("r6 與 r4 的差異僅一項：每候選 trial 上限由21,600秒改為64,800秒（18小時）。候選數、總時間、角度、門檻、動作清單、品質契約、關節契約、凍結姿勢與保護區規則皆同。候選次數與時間延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art(PREVIOUS_REQUEST), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(PREV_DIR + "/quality-ledger.json"), "freeze": art(PREV_DIR + "/freeze.json"), "earlier_version": old["phase_history"]["previous_version"],
                                              "withdrawn_draft_skipped": {"request": "requests/ro-swordsman-character-v1-r5.json", "record": art("runs/qa/ro-swordsman-character-v1-r5/withdrawn.json")},
                                              "reason": "P2到P5屬同一候選，v001已用5,328秒，P3到P5估計需10到16小時，超過每候選21,600秒上限；見 runs/qa/ro-swordsman-character-v1/v001/p3-plan-review-01.md",
                                              "authority": AUTH, "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選；已用時間延續）",
                                              "quality_targets_lowered": False, "thresholds_changed": "無；只改每候選時間上限"}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate",
                "holdout_policy", "support_envelope", "open_questions"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["budget"].items() if k not in ("trial_seconds", "basis")}, {k: v for k, v in d["budget"].items() if k not in ("trial_seconds", "basis")})
    assert same({k: v for k, v in old["quality"].items() if k not in ("status", "budget")}, {k: v for k, v in d["quality"].items() if k not in ("status", "budget")})
    assert d["quality"]["budget"]["total_seconds"] == old["quality"]["budget"]["total_seconds"] and d["assumptions"][:-1] == old["assumptions"]
    dump(NEW_REQUEST, d)
    record_path = "runs/qa/ro-swordsman-character-v1/authorizations.json"
    record = json.loads((ROOT / record_path).read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "text": AUTH,
                              "covers": ["預算做法1：另立 ro-swordsman-character-v1-r6，只把每候選 trial 上限由21,600秒改為64,800秒；候選數4、總上限172,800秒不變；已用時間延續；凍結並重新登記baseline",
                                         "扭轉骨做法1：helper 規則加『只跟隨扭轉』模式（Python 與 JS 同步並加測試）；wrist_transition.R_twist／L_twist 各跟隨同側 hand 繞前臂軸扭轉的50%；移除 two_hand_chop 候選姿勢中手打的扭轉 key（凍結的四根手臂旋轉不變）；重跑關節範圍與閉環；雙手下劈若50%不過，最多再試2個比例",
                                         "第一個候選 v001 延續"],
                              "interpretation": "r4／r6 的 frozen_poses 只凍結 upper_arm／lower_arm 四根旋轉，註記『手與手指的旋轉屬候選資料』；扭轉骨不在凍結值內，因此新的候選姿勢檔不需要再升需求版本。",
                              "not_covered": ["其他門檻或驗收的任何放寬", "清掉肩甲實驗中間檔", "保護區C其餘項目", "保護區D其餘項目", "Unity或其他目標環境", "commit／push"]})
    record["applies_to"].append("ro-swordsman-character-v1-r6")
    dump(record_path, record, mode="w")
    print("draft written", workbench.validate_request(d))

elif stage == "freeze":
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "draft" and not d["open_questions"]
    d["status"], d["quality"]["status"] = "specified", "frozen"
    assert not workbench.validate_request(d) and not workbench.readiness(d)
    dump(NEW_REQUEST, d, mode="w")
    contract = d["support_envelope"]["joint_range_contract"]
    assert sha(contract["path"]) == contract["sha256"]
    dump(NEW_DIR + "/freeze.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "turn_start_utc": sys.argv[2], "authority": AUTH,
                                    "request": {"path": NEW_REQUEST, "file_sha256": sha(NEW_REQUEST),
                                                "request_sha256": workbench.request_sha256(d), "protocol_sha256": workbench.quality_sha256(d)},
                                    "joint_range_contract": contract, "max_candidate_trials": d["production"]["max_revisions"], "budget": d["quality"]["budget"],
                                    "required_checks": [c["id"] for c in workbench.required_checks(d)], "authorization_record": "runs/qa/ro-swordsman-character-v1/authorizations.json",
                                    "rule": "The request file must not change after this point; a contract change needs a new request version and baseline."})
    dump(PREV_DIR + "/closure.json", {"closed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "request": "ro-swordsman-character-v1-r4",
                                      "result": "superseded before any candidate was recorded", "reason": "Per-candidate trial cap too small for one candidate's P2-P5 lifecycle; only the cap changes in r6.",
                                      "evidence": "runs/qa/ro-swordsman-character-v1/v001/p3-plan-review-01.md", "successor": NEW_REQUEST,
                                      "ledger_trials": ["baseline"], "candidates_recorded": 0, "candidate_in_progress_carried_over": "v001", "files_kept_unchanged": True, "authority": AUTH})
    print("frozen", workbench.request_sha256(d))

elif stage == "baseline":
    # As in earlier versions, version setup time is booked to the baseline (cumulative), not to the candidate in progress.
    setup_start, ended, setup_seconds = sys.argv[2], sys.argv[3], float(sys.argv[4])
    d = json.loads(NEW.read_text(encoding="utf-8"))
    assert d["status"] == "specified" and d["quality"]["status"] == "frozen"
    previous_ledger = json.loads((ROOT / PREV_DIR / "quality-ledger.json").read_text(encoding="utf-8"))
    previous = previous_ledger["trials"][0]
    started, elapsed = previous["started_utc"], previous["elapsed_seconds"] + setup_seconds
    # Same contract, same baseline file: the r4 measurement stands; only the request binding changes.
    assert previous_ledger["joint_range_contract"] == d["support_envelope"]["joint_range_contract"]
    request_sha, protocol_sha = workbench.request_sha256(d), workbench.quality_sha256(d)
    evidence = {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "checks": copy.deepcopy(previous["evidence"]["checks"]),
                "deliverables": previous["evidence"]["deliverables"], "subject_artifacts": previous["evidence"]["subject_artifacts"]}
    trial = {"id": "baseline", "parent_id": None, "status": "completed", "started_utc": started, "ended_utc": ended, "elapsed_seconds": elapsed,
             "protocol_sha256": protocol_sha, "reviewer": previous["reviewer"] + "; carried to r6 unchanged (same contract, file, views and scores)",
             "previews": previous["previews"], "scores": previous["scores"], "evidence": evidence,
             "r6_setup_interval": {"start_utc": setup_start, "end_utc": ended, "seconds": setup_seconds}}
    dump(NEW_DIR + "/quality-ledger.json", {"schema_version": 1, "request_id": d["id"], "request_sha256": request_sha, "protocol_sha256": protocol_sha,
                                            "joint_range_contract": d["support_envelope"]["joint_range_contract"], "trials": [trial],
                                            "phase_history": {"previous_ledger": art(PREV_DIR + "/quality-ledger.json"), "previous_phase_reopened": False, "quality_targets_lowered": False,
                                                              "elapsed_carried_from_previous_version_seconds": previous["elapsed_seconds"]}})
    result = subprocess.run([sys.executable, "-B", "scripts/workbench.py", "compare", NEW_REQUEST, "--ledger", NEW_DIR + "/quality-ledger.json"], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    assert result.returncode == 0, result.stderr
    with open(ROOT / NEW_DIR / "comparison-baseline.json", "x", encoding="utf-8", newline=NL) as handle:
        handle.write(result.stdout)
    print("baseline registered", json.loads(result.stdout)["next_action"])
