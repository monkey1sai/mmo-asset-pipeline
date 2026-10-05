"""Record the outcome of the pre-freeze review: tolerances from measurement, single clock, disposition, incident recovery.

Run from the repo root: python -B runs/qa/ro-swordsman-character-v1/p2-prep/record-review-outcome-used.py
The request stays draft. New record files are created once and never overwritten.
"""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
P = "runs/qa/ro-swordsman-character-v1/p2-prep"
NL = chr(10)


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write_new(path, payload):
    with open(ROOT / path, "x", encoding="utf-8", newline=NL) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write(NL)


now = datetime.datetime.now(datetime.timezone.utc).isoformat()
request_path = ROOT / "requests/ro-swordsman-character-v1.json"
d = json.loads(request_path.read_text(encoding="utf-8"))
d["runtime_contract"]["tolerances_m"] = {
    "export_roundtrip_fresh_blender_world": 5e-6, "runtime_cpu_evaluated_world": 1e-5,
    "measured_basis": {"as_exported": P + "/weights-probe/roundtrip-as-exported.json", "exact_weights": P + "/weights-probe/roundtrip-exact-weights.json",
                       "observed": "基準完整角色8個取樣：匯出原樣最大14.55µm；還原精確權重後最大1.048µm（rest姿勢即0.861µm），47個頂點取樣超過1µm。"},
    "rationale": "完整角色頂點距原點1–1.7m，GLB的float32位置與反綁定矩陣使世界座標回讀的精度下限約1µm，1µm門檻在整個角色上無法保證。"
                 "r010的1µm是手部局部座標原型的門檻，其原檔與結果保留為回歸證據、不得改動。完整角色世界座標回讀定為5µm，runtime CPU求值點10µm；"
                 "兩者都要求先還原被匯出器略去的極小權重。",
    "requires": "scripts/cv1_restore_glb_weights.py 還原全部蒙皮網格的來源權重後才量測",
}
d["assumptions"] = [a for a in d["assumptions"] if not a.startswith("匯出回讀容差沿用r010的1µm") and not a.startswith("時鐘：每個trial記錄兩種時間")]
d["assumptions"] += [
    "匯出回讀容差：完整角色世界座標5µm、runtime CPU求值點10µm，依2026-10-05基準實測訂定（還原精確權重後最大1.048µm）；r010手部局部原型的1µm結果保留為回歸證據。",
    "時鐘（單一口徑）：trial 的 elapsed_seconds 是協調者實際工作時間，即各回合開始到結束的時間相加，含量測、等待工具與審查；等待使用者回覆的區間不計入，逐筆記錄起訖供查核。",
]
d["budget"]["clock_rule"] = ("baseline與準備時間計入階段總時間；失敗、被淘汰與預檢失敗的候選不釋出次數；不以改名或新seed延長。"
                             "elapsed_seconds 採協調者實際工作時間（各回合起訖相加），等待使用者回覆的區間不計入並逐筆記錄。")
request_path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + NL, encoding="utf-8", newline=NL)

findings = [
    (1, "High", "工具新增 deforms 關卡：每根被擺動的骨須有>=3個權重>=0.1的頂點且典型角度位移>=0.1mm。基準的 toe-extension.L/R 現在因 toe 無權重而不通過。",
     "無 expect 的扭轉與張指動作只驗有位移，未驗方向符號。"),
    (2, "High", "手區交叉在組合姿勢（握拳除外）與非手部動作的極端角度也強制為0；手區以外在典型與極端角度都受基準上限約束，另加極端角度邊長比上限。",
     "握拳與腕指掃描的極端角度手區交叉仍只報告，交美術審查；接觸與穿入的深度量測未實作。"),
    (3, "High", "改以手部骨權重定義手區，武器以外所有蒙皮網格合成單一集合計算跨網格交叉；移除依網格名稱的零容忍清單。",
     "手區以外只是防退步上限：基準在髖前屈、深蹲等動作的大量穿插仍被容許，須靠美術審查。"),
    (4, "High", "新增 holdout_policy：固定名稱與需求雜湊外的紀錄檔、通過條件含全部clip檢查、允許與禁止的新增內容；runtime_contract 限定互動狀態只能由宣告時窗以固定過渡產生。",
     "承諾雜湊需使用者提供；未提供時無法事後證明holdout未被更換。"),
    (5, "Medium", "baseline登記腳本補 target_environment 檢查；授權紀錄移到 authorizations.json（不在需求雜湊範圍）。", "無"),
    (6, "Medium", "新增 grasp_gate，逐字引用 r010 functional_gate、original_shape_guard、interval 規則與「失敗後不得移動建立時刻」，並註明灰模接受屬通過條件。",
     "左手沿用鏡射pad是新增定義，r010沒有左手。"),
    (7, "Medium", "新增 contact_measurement、transition_matrix.gates、肩與髖軸向旋轉、握劍＋腕動作的 requires_pose 組合。", "名義速度與床面量點是設計值，未經實測校正。"),
    (8, "Medium", "改為單一口徑（協調者實際工作時間），刪除「可改採牆鐘重算」。", "需使用者明確同意；同意前不凍結。"),
    (9, "Low", "工具必須明示 --rules 或 --no-rules、以修改器判定蒙皮網格、可用 --request 核對契約SHA；rest既有交叉改為手區內必須0、手區外不得超過基準；需求區塊改名去除 draft／proposal。",
     "rest時手區對其他部位既有的交叉（基準4對）不設上限，只報告。"),
]
write_new(P + "/independent-contract-review-disposition.json", {
    "observed_utc": now, "review": {"path": P + "/independent-contract-review.md", "sha256": sha(P + "/independent-contract-review.md")},
    "note": "每項皆先核對再處置；審查意見是模型產出，不是人類批准。九項全部核對屬實。",
    "findings": [{"n": n, "severity": severity, "verdict": "confirmed", "action": action, "residual": residual} for n, severity, action, residual in findings],
    "uncertainty_resolved": {"one_micron_whole_body": "實測不可保證：還原精確權重後最大1.048µm。需求改訂完整角色世界座標5µm，需使用者知悉。"},
    "side_effect": "回讀驗證腳本第一次執行時造成Blender擴充套件快取被清空，見 incident-blender-extension-cache.json；已恢復。",
})
write_new(P + "/incident-blender-extension-cache-recovery.json", {
    "observed_utc": now, "incident": {"path": P + "/incident-blender-extension-cache.json", "sha256": sha(P + "/incident-blender-extension-cache.json")},
    "user_action": "使用者關閉並正常重開Blender（新程序 PID 46236，12:35 啟動）。",
    "verified_read_only": {"site_packages_top_level_entries": 215, "dist_info_folders": 98, "stale_folders": 0, "files": 11532,
                           "spot_checked_present": ["ifcopenshell", "aiohttp", "pandas", "lxml", "shapely", "PIL", "bonsai"]},
    "expected_recovery_confirmed": True, "not_verified": "沒有在Blender內實際操作Bonsai功能。",
    "recurrence_check": "移除該指令後，本回合其後各次Blender執行未再出現刪除訊息；快取目錄修改時間維持12:35。",
})

# Baseline registration script: v2 evidence, the 19th required check, current numbers.
script = ROOT / P / "register-baseline-used.py"
s = script.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:50]
    s = s.replace(old, new)


rep('JOINTS = art(f"{QA}/p2-prep/baseline-joint-range/joint-range-result.json")',
    'JOINTS = art(f"{QA}/p2-prep/baseline-joint-range-v2/joint-range-result.json")' + NL + 'ROUNDTRIP = art(f"{QA}/p2-prep/weights-probe/roundtrip-as-exported.json")')
rep('"Joint-range sweep on this file: 17 of 61 contract motions fail or cannot be measured (triangle collapse at shoulders, elbow and spine twist; self-intersections on the exposed right hand and wrist at typical angles)."',
    '"Joint-range sweep on this file: 36 of 73 contract motions fail or cannot be posed (triangle collapse at shoulders, elbow and spine twist; hand-region intersections at typical angles; toes carry no weights)."')
rep('"scripts/cv1_joint_range.py with the frozen contract: numeric gate false, 12 motions fail and 5 are missing bones."',
    '"scripts/cv1_joint_range.py with the frozen contract: numeric gate false, 27 motions fail and 9 cannot be posed (5 missing bones, 4 missing the grasp pose)."')
rep('"Five contract motions cannot be posed because the bones are missing."', '"Five contract motions cannot be posed because the bones are missing, and no grasp pose asset exists."')
rep('"P1 export of this file: exporter drops skin weights <= 1e-4 and the runtime residual reaches 14.7 um, above the 1 um readback tolerance; no fresh-Blender reimport of a full clip set exists.", P1, P1_REPORT)',
    '"Fresh-Blender readback of this file as exported: maximum 14.55 um on 8 samples, above the 5 um world-space tolerance, because the exporter drops skin weights <= 1e-4; no listed clip exists to read back.", ROUNDTRIP, P1_REPORT)')
rep('    "art-motion-review": check(',
    '    "target_environment": check("fail", "Three.js 0.186.0 QA scene loaded this file only for the P1 wiring probe; none of the listed clips, transitions or corrective rules exists to verify in the target environment.", P1, P1_REPORT),'
    + NL + '    "art-motion-review": check(')
script.write_text(s, encoding="utf-8", newline=NL)
print("recorded")
