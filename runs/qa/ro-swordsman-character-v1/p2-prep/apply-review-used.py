"""Apply the pre-freeze independent review to requests/ro-swordsman-character-v1.json (still draft afterwards).

Run from the repo root: python -B runs/qa/ro-swordsman-character-v1/p2-prep/apply-review-used.py
Covers review findings 2-9 on the contract side; finding 1 and the tool part of 3 and 9 are in scripts/cv1_joint_range.py.
Original acceptance is not lowered: style, size, budgets, the 300-frame combo contract and the quality contract are asserted unchanged.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
QA = ROOT / "runs/qa/ro-swordsman-character-v1"
REQUEST = ROOT / "requests/ro-swordsman-character-v1.json"
R010 = ROOT / "runs/qa/ro-swordsman-combo-r010/local-contract.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


d = json.loads(REQUEST.read_text(encoding="utf-8"))
r010 = json.loads(R010.read_text(encoding="utf-8"))
frozen_before = json.dumps([d["style"], d["quality"], {k: v for k, v in d["spec"].items() if k not in ("clip_contracts_draft", "animations")}], sort_keys=True, ensure_ascii=False)

# Finding 9: one name per block, no stale "draft"/"proposal" wording next to frozen status.
d["spec"]["clip_contracts"] = d["spec"].pop("clip_contracts_draft")
d["budget"] = d.pop("budget_proposal")
d["protected_zone"] = d.pop("protected_zone_proposal")
d["transition_matrix"] = d.pop("transition_matrix_draft")
d["runtime_contract"] = d.pop("runtime_contract_draft")
d["assumptions"] = [a for a in d["assumptions"] if not a.startswith("clip長度、關節範圍、接觸門檻、轉場矩陣為待凍結提案")]
d["assumptions"].append("30/60/120fps、0.5x/1x/1.5x、100/200/400ms是測試工況，不是性能證明。")

# Finding 5: authorizations and later protected-zone grants live outside the hashed request, so recording one does not void the ledger.
authorizations = {"request_id": d["id"], "note": "授權逐筆追加，不改寫舊紀錄。此檔不在需求雜湊範圍內；需求只凍結授權當時已生效的內容。",
                  "entries": d["phase_history"].pop("authorizations"),
                  "protected_zone": {item["id"]: item.pop("authorization") for item in d["protected_zone"]["requires_authorization"]}}
d["budget"].pop("authority", None)
d["budget"]["status"] = "authorized"
d["protected_zone"].pop("authority", None)
d["protected_zone"]["status"] = "see_authorization_record"
d["phase_history"]["authorization_record"] = "runs/qa/ro-swordsman-character-v1/authorizations.json"
d["protected_zone"]["rule"] = "A、B已授權。C、D與任何其他保護區變更須先在授權紀錄檔新增一筆使用者授權才可動工；未授權的保護區變更使候選失敗。"

# Finding 6: the grasp rule is the r010 rule, quoted, not paraphrased.
grasp = {
    "source": {"path": R010.relative_to(ROOT).as_posix(), "sha256": sha(R010)},
    "functional_gate_verbatim": r010["functional_gate"], "original_shape_guard_verbatim": r010["original_shape_guard"],
    "pads_verbatim_reference": "local-contract.json#pads（finger1 31／finger2 44／finger3 54／finger4 40／thumb 77 點），遮罩不改、不換近點",
    "interval_rules_verbatim": {k: r010["interval"][k] for k in ("supplemental_half_frames", "rigid_weapon_follow_hand_required", "no_perframe_weapon_sliding")},
    "establishment_rule": "每個握持時窗的建立幀在量測前宣告；失敗後不得移動建立時刻（r010 activation: no moving establishment time after failure）。",
    "window_scope": "上述全部條件在各clip宣告的握持時窗內逐取樣強制；時窗外不要求接觸，但 unknown/inside 0、手劍橫向交叉 0、樣本穿入<=1mm 仍適用。",
    "gray_acceptance": "independentgrayshapeacceptance 屬本檢查的通過條件之一，由獨立審查者判定，不得以數值通過代替。",
    "hand_identity": "右手沿用r010的904點來源ID與原五指pad；左手鏡射後以鏡射ID對應同一組pad。",
}
d["grasp_gate"] = grasp
for check in d["additional_checks"]:
    if check["id"] == "grasp-contact-windowed":
        check["description"] = ("r010 握持功能關卡原文：" + r010["functional_gate"] + " 另含原形狀防護（邊長比0.25–3）、武器剛性跟手、不得逐幀滑動、失敗後不得移動建立時刻；"
                                "於各clip宣告的握持時窗內逐取樣強制，時窗外仍查穿入與交叉。細節見 grasp_gate。")
    if check["id"] == "transition-interaction":
        check["description"] = "transition_matrix 所列轉場×時長×播放速度×求值步進逐一取樣，依 transition_matrix.gates 判定；含pause/resume/seek、loop接縫與反覆切換、武器socket與床面支撐時窗。"
    if check["id"] == "frozen-holdout-reuse":
        check["description"] = ("凍結mesh／rest骨架／權重／通用morph／驅動規則／runtime求值器後接入holdout動作；只新增clip／骨對應／事件／互動時窗；各資料類別以正規化簽章逐一比較不變，"
                                "且holdout必須通過與其他clip相同的 clip-set、握持、轉場與美術檢查。細節見 holdout_policy。")
    if check["id"] == "joint-range":
        check["description"] = "support_envelope.joint_range_contract 綁定的契約由 scripts/cv1_joint_range.py 執行：全部動作的數值關卡通過，加固定視角同尺度灰模的獨立審查。"

# Findings 2, 3: gates described as the tool now enforces them.
envelope = d["support_envelope"]
envelope.pop("zero_self_intersection_meshes", None)
envelope["joint_ranges_deg"]["shoulder"]["axial_rotation"] = 60
envelope["joint_ranges_deg"]["hip"]["axial_rotation"] = 35
envelope["combination_poses"] = ["抬臂過頭", "雙手下劈", "深蹲／落地", "空手握拳（不得出現劍柄壓痕）", "張掌施法（左手）",
                                 "握劍＋腕屈伸／橈尺偏（需要候選的FK握姿 grasp.R）", "仰臥睡姿（於睡眠clip評估）"]
envelope["joint_range_gates"] = {
    "subject": "武器以外所有蒙皮網格合成單一三角形集合量測，跨網格穿插計入；手區＝任一頂點的手部骨（hand／finger／thumb／wrist_transition）權重合計>=0.5的三角形，與所在網格無關。",
    "missing": "契約列出的骨或姿勢不存在即該動作不通過",
    "direction": "典型角度時，指定骨尾端位移在預期方向的分量>0",
    "deforms": "每根被擺動的骨必須有>=3個權重>=0.1的頂點，且典型角度時最大位移>=0.1mm；沒有權重的骨不算通過",
    "collapse": "典型與極端角度皆不得有求值後面積小於rest面積5%的三角形",
    "hand_self": "手區內部自交對數為0：rest與典型角度一律適用；組合姿勢（握拳除外）與非手部動作的極端角度也適用",
    "hand_other": "手區對其他部位相對rest新增的交叉對數為0，適用層級同上",
    "hand_shape_guard": "手區邊長比在典型與極端角度皆須在0.25–3（沿用r010原形狀防護）",
    "body_ratchet": "手區以外：rest既有交叉對數不得超過基準；各動作在典型與極端角度相對rest新增的交叉對數與極端角度最大邊長比不得超過基準同一動作的值。這是防退步上限，不是接受基準的缺陷。",
    "reported_only": "腕、指、拇指掃描與握拳在極端角度的手區交叉只報告，交由灰模美術審查",
    "art": "每個部位的同尺度灰模由獨立審查者判定；數值通過不代表美術通過",
}

# Finding 7: measurement definitions fixed before any clip exists.
envelope["contact_measurement"] = {
    "floor": "地面為世界 Z=0 平面（Blender）／Y=0（GLB）",
    "sole_set": "腳底量點＝rest時 foot／toe 骨權重合計>=0.5 且高度在該腳最低點以上10mm內的頂點；於角色基礎凍結時以頂點ID清單與SHA固定，之後不得更換。",
    "foot_slide": "stance時窗內 sole_set 質心相對時窗第一個取樣的水平位移最大值；原地循環的Walk／Run先扣除名義速度造成的等速後移。",
    "nominal_speed_m_s": {"AN_RO_Walk_Sword": 1.4, "AN_RO_Run_Sword": 3.5},
    "foot_penetration_float": "stance時窗內 sole_set 最低點低於地面的最大深度／高於地面的最大高度",
    "bed": "床面為代理頂面平面；支撐區量點＝背、骨盆、後腦、小腿各自 rest 時最靠後10mm內的頂點，同樣於基礎凍結時固定。",
    "sampling": "每個clip整幀＋半幀；握持建立、放劍／取劍、腳著地與離地前後各加密到1/4幀。只宣稱受測時間點。",
    "window_lock": "每個clip的接觸時窗、事件幀與名義速度寫在該clip的互動設定檔，於該clip第一次量測前登記SHA；量測失敗後修改時窗視為實作修復，保留原失敗紀錄，且仍受 contact_window_rules 的最低涵蓋限制。",
}
d["transition_matrix"]["gates"] = {
    "collapse": "轉場期間任何取樣不得有面積比<5%的三角形",
    "hand": "手區自交與相對rest新增交叉為0",
    "grasp": "兩端clip在該時刻都屬握持時窗時，握持功能關卡持續成立；武器剛性跟手、不得滑動",
    "weapon_body": "武器對身體網格的取樣穿入<=1mm",
    "feet": "兩端都屬stance的腳，轉場期間滑動不超過 foot_stance_slide_mm 的2倍",
    "continuity": "轉場起點與終點的骨骼姿勢與來源clip在該時刻的姿勢一致（每骨<=0.5度、根位置<=1mm）",
    "determinism": "同一時間與狀態，不論經由播放、pause/resume 或 seek 抵達，求值後頂點位置相差<=1e-9m（求值器不得帶歷史狀態）",
    "loop_seam": "loop clip 最後一幀接第一幀：每骨<=1度、sole_set與握持點位置<=1mm",
}
d["runtime_contract"]["interaction_state"] = ("互動狀態（如 grasp.R）只能由各clip宣告的時窗產生：時窗內1、時窗外0，邊界以固定12幀線性過渡；不得為個別clip編寫狀態曲線。"
                                             "同一狀態值在所有clip對應同一組修形權重。")

# Finding 4: holdout pass condition and rotation that does not require editing the request.
d["holdout_policy"] = {
    "name": "AN_RO_Holdout_01 是『當前凍結版本的holdout』的固定名稱；輪替時沿用此名，實際內容記於 holdout 紀錄檔（不在需求雜湊範圍內）。",
    "record": "runs/qa/ro-swordsman-character-v1/holdout-record.json",
    "commitment": "使用者可在凍結前提供holdout描述文字的SHA-256作為承諾；揭示時核對。未提供時紀錄檔註明無承諾雜湊。",
    "reveal": "只在角色基礎各資料類別的簽章登記完成後揭示。",
    "allowed_additions": ["holdout clip的骨骼動畫", "骨對應", "事件", "依 contact_window_rules 宣告的互動時窗"],
    "forbidden": ["修改mesh／rest骨架／權重／通用morph／驅動規則／runtime求值器", "新增morph通道或規則", "為holdout編寫互動狀態曲線", "依動畫名稱或幀號的特判"],
    "pass": "簽章逐類不變，且holdout通過 clip-set、grasp-contact-windowed（若含握持）、transition-interaction（Idle<->Holdout）、runtime-closed-loop 與獨立美術審查。",
    "failure": "承認該版本能力缺口；修正須升版並計1個候選；失敗的holdout轉為回歸clip；下一個凍結版本使用使用者另行保管的新holdout。",
}
d["assumptions"] = [a for a in d["assumptions"] if not a.startswith("holdout：使用者2026-10-05採做法1")]
d["assumptions"].append("holdout：使用者2026-10-05採做法1，已私下選定並自行保管，角色基礎凍結後才揭示；規則見 holdout_policy。")

REQUEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
record = QA / "authorizations.json"
with open(record, "x", encoding="utf-8", newline="\n") as handle:
    json.dump(authorizations, handle, ensure_ascii=False, indent=1)
    handle.write("\n")
frozen_after = json.dumps([d["style"], d["quality"], {k: v for k, v in d["spec"].items() if k not in ("clip_contracts", "animations")}], sort_keys=True, ensure_ascii=False)
assert frozen_before == frozen_after and d["status"] == "draft"
print(json.dumps({"request_file_sha256": sha(REQUEST), "authorization_entries": len(authorizations["entries"]), "protected_zone": authorizations["protected_zone"]}, ensure_ascii=False))
