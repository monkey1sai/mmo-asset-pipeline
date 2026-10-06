"""Write the pre-freeze contract terms into requests/ro-swordsman-character-v1.json (still draft after this).

Run from the repo root: python -B runs/qa/ro-swordsman-character-v1/p2-prep/finalize-request-used.py
Original acceptance (style, size, triangle budget, 300-frame combo contract, six quality dimensions) is not touched.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PREP = ROOT / "runs/qa/ro-swordsman-character-v1/p2-prep"
REQUEST = ROOT / "requests/ro-swordsman-character-v1.json"
AUTH = "holdout 用做法 1，我已選好；開始 P2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


d = json.loads(REQUEST.read_text(encoding="utf-8"))
before = sha(REQUEST)
original = {key: json.dumps(d[key], sort_keys=True, ensure_ascii=False) for key in ("style",)}
quality_before = json.dumps({k: v for k, v in d["quality"].items() if k != "status"}, sort_keys=True, ensure_ascii=False)
combo_before = json.dumps({k: v for k, v in d["spec"]["animation_contract"].items() if k != "scope_note"}, sort_keys=True)

d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）"
d["open_questions"] = []
d["assumptions"] += [
    "holdout：使用者2026-10-05採做法1，已私下選定並自行保管，角色基礎凍結後才揭示。AN_RO_Holdout_01 是佔位名稱；製作階段不知道其內容。",
    "時鐘：每個trial記錄兩種時間。elapsed_seconds 為協調者實際工作時間（各回合起訖相加，含量測、等待工具與審查）；等待使用者專屬輸入（holdout揭示、驗證、授權）的區間逐筆另記，不計入 elapsed_seconds。牆鐘總時間同時保存，使用者可改採牆鐘口徑重算。",
    "同一trial可跨多個回合；trial內的實作修復保留先前失敗與原時鐘。P2到P5屬同一候選的生命週期：compare 對任何非美術必要檢查失敗的completed候選一律discard，所以候選要帶著全部必要檢查才登記completed。",
    "灰模先行：候選先以關節範圍灰模與固定五視角做內部檢視，再投入完整clip、runtime與匯出驗證；內部檢視不取代登記時的全部必要檢查。",
    "匯出回讀容差沿用r010的1µm（同版本Blender來源對GLB重匯入）；runtime CPU求值點容差10µm。兩者都要求先還原被匯出器略去的極小權重。",
]
d["support_envelope"]["status"] = "frozen_with_request"
d["support_envelope"]["note"] = "角度為相對rest的單軸活動範圍（度）。2026-10-05以基準角色實跑校正：角度未調整；校正結果只用來訂量測門檻與基準上限。凍結後不得為過關而縮小。"
d["support_envelope"]["zero_self_intersection_meshes"] = ["SM_RO_hand.R", "SM_RO_hand.L", "SM_RO_WristLoft.R", "SM_RO_WristLoft.L", "SM_RO_glove.R"]
d["support_envelope"]["calibration"] = {
    "result": "runs/qa/ro-swordsman-character-v1/p2-prep/baseline-joint-range-calibration/joint-range-result.json",
    "sha256": sha(PREP / "baseline-joint-range-calibration/joint-range-result.json"),
    "draft_contract": "runs/qa/ro-swordsman-character-v1/p2-prep/joint-range-contract-draft.json",
    "observed": "56個動作量測、5個因缺骨無法量測；基準在肩、肘、髖、膝、右手多處於典型角度即出現新增自交，肩前舉極端邊長比37倍。",
}
d["support_envelope"]["joint_range_gates"] = {
    "missing_bone": "契約列出的骨不存在即該動作不通過",
    "direction": "典型角度時，指定骨尾端位移在預期方向的分量>0",
    "collapse": "典型與極端角度皆不得有求值後面積小於rest面積5%的三角形",
    "typical_self_intersection": "典型角度：外露的手與腕網格新增自交對數必須為0；其餘網格不得超過基準在同一動作、同一網格的對數（防退步上限，不是接受這些自交）",
    "reported_only": "極端角度的自交對數與邊長比只報告，交由灰模美術審查",
    "art": "每個部位的同尺度灰模由獨立審查者判定；數值通過不代表美術通過",
}
d["support_envelope"]["contact_window_rules"] = {
    "note": "各clip的接觸時窗在量測該clip之前於互動設定宣告；下列為最低涵蓋，防止以縮短時窗過關。",
    "grasp_R": "Idle、Walk、Run、Cast、Combo全程；LieDown自開始至放劍事件、GetUp自取劍事件至結束。放劍事件不得早於LieDown的25%，取劍事件不得晚於GetUp的75%。",
    "foot_stance": "Idle雙腳全程；Walk每腳stance至少40%週期；Run每腳stance至少20%週期；Cast雙腳全程。",
    "bed_support": "LieDown的支撐建立幀不得晚於該clip的70%；Sleep_Loop全程；GetUp至離床幀，離床幀不得早於該clip的30%。",
}
clips = d["spec"]["clip_contracts_draft"]
clips["status"] = "frozen_with_request"
clips["note"] = "長度、loop、事件與接觸為凍結值；holdout由使用者保管。所有clip以60fps製作。"
for clip in clips["clips"]:
    clip["frames"] = clip.pop("frames_proposed")
d["transition_matrix_draft"]["status"] = "frozen_with_request"
runtime = d["runtime_contract_draft"]
runtime["status"] = "frozen_with_request"
runtime["clip_time_origin"] = "交付用clip的第一個key在t=0（匯出時slide to zero）；QA以clip實際key時間核對後才量測，frame f 對應 (f - 起始frame)/fps。"
runtime["tolerances_m"] = {"export_roundtrip_fresh_blender": 1e-6, "runtime_cpu_evaluated": 1e-5,
                           "rationale": "1µm沿用r010回讀門檻；10µm為runtime float32路徑的界線，P1觀測未受權重略去影響的網格最大0.68µm、受影響者14.7µm，故此門檻要求先還原精確權重。"}
d["budget_proposal"]["clock_rule"] += " elapsed_seconds 採協調者實際工作時間；等待使用者專屬輸入的區間另記不計入，牆鐘同時保存。"
d["phase_history"]["authorizations"].append({"utc_date": "2026-10-05", "text": AUTH, "covers": ["holdout做法1（使用者私下保管，凍結後揭示）", "開始P2"],
                                              "not_covered": ["保護區C、D", "commit／push", "Unity或其他目標環境"]})

# The joint-range contract is built from this request, then bound back by hash.
REQUEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
contract = PREP / "joint-range-contract.json"
subprocess.run([sys.executable, "-B", str(ROOT / "scripts/cv1_joint_contract.py"), str(REQUEST), str(contract),
                "runs/qa/ro-swordsman-character-v1/p2-prep/baseline-joint-range-calibration/joint-range-result.json"], check=True, cwd=ROOT)
d["support_envelope"]["joint_range_contract"] = {"path": contract.relative_to(ROOT).as_posix(), "sha256": sha(contract)}
REQUEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

assert original["style"] == json.dumps(d["style"], sort_keys=True, ensure_ascii=False)
assert quality_before == json.dumps({k: v for k, v in d["quality"].items() if k != "status"}, sort_keys=True, ensure_ascii=False)
assert combo_before == json.dumps({k: v for k, v in d["spec"]["animation_contract"].items() if k != "scope_note"}, sort_keys=True)
assert d["status"] == "draft" and d["quality"]["status"] == "draft"
print(json.dumps({"request_sha256_before": before, "request_sha256_after": sha(REQUEST), "joint_range_contract": d["support_envelope"]["joint_range_contract"]}, indent=1))
