# 凍結前獨立契約審查（唯讀子代理回報，原文）

時間：2026-10-05。審查者：本 session 派出的唯讀子代理（只有 Read／Grep／Glob），未給協調者的結論。
這是模型產出的審查意見，不是人類批准，也不是計入的簽核。協調者的處置見 `independent-contract-review-disposition.json`。

---

**狀態**：已完成（唯讀審查，未改任何檔）。凍結前發現 High 4、Medium 4、Low 1；原驗收只有握持規則被放寬。目前沒有背景工作繼續執行。

## Worker Output Contract

**Scope**：根目錄 `C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop`，以下代號皆在其下。
- request＝`requests\ro-swordsman-character-v1.json`
- contract＝`runs\qa\ro-swordsman-character-v1\p2-prep\joint-range-contract.json`
- tool＝`scripts\cv1_joint_range.py`；rules＝`scripts\cv1_pose_rules.py`；workbench＝`scripts\workbench.py`
- base＝`runs\qa\ro-swordsman-character-v1\p2-prep\baseline-joint-range\joint-range-result.json`
- register／finalize＝同目錄 `register-baseline-used.py`／`finalize-request-used.py`
- r010＝`runs\qa\ro-swordsman-combo-r010\local-contract.json`；loop＝`docs\art-quality-loop.md`
- 也讀了兩份舊需求、交接文件、`scripts\cv1_joint_contract.py`。未審 JS runtime。

**Evidence**：只用 Read/Grep/Glob，未執行命令、未重算 SHA。Verified＝直接讀到；Inference＝推測。

**Finding**

[Severity: High] 1. 關節掃描讓沒變形的動作靜默通過（問5）
- Location: tool:113-128,259-281
- Category: correctness
- Failure scenario: 新增的骨不配權重，DIP 與拇指 IP 動作即空轉通過；無 `expect` 的 14 個動作完全不驗姿勢是否擺到位。
- Evidence: Verified。base 的 `toe-extension.L/R` 邊長比恆 1.0 仍 `pass:true`（toe 權重頂點 0）。
- Refutation check: 無其他把關。
- Suggested direction: 斷言實際角度與權重頂點位移。

[Severity: High] 2. 握拳與壓力姿勢只在 50% 幅度受檢（問2）
- Location: contract:27-30,41-90；request:642-649
- Category: correctness
- Failure scenario: 修掉個位數塌陷三角即過「抬臂過頭」，滿幅仍有 1088 對自交、37 倍拉伸。
- Evidence: Verified。NO_SHIP 基準的 `combo-deep-squat` 已通過（滿幅 754 對）。
- Refutation check: art 失敗不被 compare 淘汰（workbench:511）。
- Suggested direction: 組合姿勢以滿幅判定；extreme 加自交與邊長比的基準上限。

[Severity: High] 3. 自交只算單一網格內，零容忍靠網格名稱（問2、5）
- Location: tool:153-181,238-240；request:629-635
- Category: correctness
- Failure scenario: 左手留在 `SM_RO_core`（基準現況）適用 44 對上限而非 0；手穿腕套、腿穿衣擺不計；core 拆件可清空計數。
- Evidence: Verified。清單 5 個名稱有 3 個在基準不存在，工具不查存在。
- Refutation check: 未知名稱預設 0，仍擋不住。
- Suggested direction: 以手部骨權重定義外露區，跨網格計數。

[Severity: High] 4. Holdout 通過條件過弱，輪替規則無法執行（問2、3、6）
- Location: request:65,131-136,225-228,491；rules:90-96
- Category: correctness
- Failure scenario: 只要簽章不變加自行宣告的時窗；每片段的互動狀態曲線可當逐幀修形（Inference）。失敗後須另選 holdout，但需求只有一個佔位，改需求即令 ledger 失效；這是唯一的循環檢查。
- Evidence: Verified（文字與程式）。
- Refutation check: must_not_have 只禁名稱與幀號特判。
- Suggested direction: 凍結前寫入 holdout 規格雜湊、通過條件與 4 個佔位；state 僅由宣告時窗產生。

[Severity: Medium] 5. 凍結後首次 compare 即 stop_blocked（問6、4）
- Location: register:44-63；workbench:231-232,504-508；request:521-534
- Category: correctness
- Failure scenario: 必要檢查 19 項，基準登記只寫 18 項（缺 `target_environment`）；日後授權保護區 C/D 若改需求，紀錄全失效。
- Evidence: Verified。
- Refutation check: 腳本尚未執行，可先修。
- Suggested direction: 補該紀錄；授權紀錄移出雜湊範圍。

[Severity: Medium] 6. 握持規則因省略而放寬（問1）
- Location: request:202,616；r010:1863-1870
- Category: correctness
- Failure scenario: r010 另要求 degenerates 0、邊長比 0.25–3、失敗後不得移動握持建立時刻，新文字未列；灰模接受是否在閘內未寫明。
- Evidence: Verified。
- Refutation check: 兩處列舉彼此也不一致。
- Suggested direction: 逐字引用 r010 `functional_gate` 與 shape guard。

問1其餘項目（style、尺寸、60,000tri、2K、300 幀契約、兩項原檢查、六維度與 target）逐項比對，未見降低。

[Severity: Medium] 7. 接觸、轉場、支援範圍有未定義項（問2、3、4）
- Location: request:98,215-218,541-622,650-655；contract:102-105
- Category: correctness
- Failure scenario: 量完才選腳底量點與走路速度；時窗可在失敗後重宣告；`transition-interaction` 無門檻；缺肩髖軸向旋轉；「握劍＋腕屈伸」延後卻無片段承接。
- Evidence: Verified（缺項）。
- Refutation check: 來源對話要求量法先入契約。
- Suggested direction: 補量測定義與缺軸；時窗量測前鎖定。

[Severity: Medium] 8. 時鐘規則在「預算同意」後才改寫（問2、4）
- Location: request:258,494,771-774；finalize:71；loop:130-131
- Category: correctness
- Failure scenario: 區間歸為等待使用者即不計時；「可改採牆鐘重算」等於事後選口徑。
- Evidence: Verified。第二筆授權只涵蓋 holdout 與開始 P2。
- Refutation check: 檔內無同意紀錄。
- Suggested direction: 取得明確同意，指定單一時鐘。

[Severity: Low] 9. 綁定缺口與過期字樣（問4、5）
- Location: tool:27-32,44-47,175；workbench:17；request:222,252,615
- Category: correctness
- Failure scenario: `--rules` 省略仍可過；未掛骨架的蒙皮網格不量；rest 已自交的三角對永久豁免；不核對契約 SHA；`_draft`／`proposed` 與 `frozen_with_request` 並存。
- Evidence: Verified。
- Refutation check: 基準上未觸發。
- Suggested direction: 加斷言與 SHA 核對，刪過期字樣。

**Uncertainty**：1µm 全身回讀能否達成沒有實測（P1 靜止姿勢已 0.827µm），做不到則四個候選都會被淘汰。未發現被吞掉的例外，但 Blender 例外時的 exit code 未實測。

**Risk**：每候選 6 小時帶齊 19 項檢查是否可行未評估；候選的實際 rig 結構未知。

**Next step**：凍結前由協調者處理 1–5，並對既有 exact-weights GLB 實跑一次 `scripts\cv1_verify_glb_roundtrip.py`；6–8 交使用者確認。我這邊無待決定事項。
