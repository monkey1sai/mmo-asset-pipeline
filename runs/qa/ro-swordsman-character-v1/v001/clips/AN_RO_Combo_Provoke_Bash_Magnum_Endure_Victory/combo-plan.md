# AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory（P3 剩餘項）製作計畫

- 授權：`runs/qa/ro-swordsman-character-v1/authorizations.json` 第 27 筆（Hyper3D 付費可用）、第 28 筆（依建議開始連段）
- 需求：`requests/ro-swordsman-character-v1-r6.json` `spec.animation_contract`（300 幀／60 fps、原地、順序 provoke→bash→magnum_break→endure→victory）、
  `quality.dimensions[use-readability]`（12 參考姿勢、重心、支撐腳、劍尖弧線；效果分離可關閉）、`additional_checks[skill-effects]`、
  `contact_window_rules`（Combo 握持全程）
- 參考：`assets/raw/ro-swordsman-combo/references-v001/`（五張技能圖、12 格動作表）

## 既有能力盤點（resource-first）

| 來源 | 可重用 | 結論 |
|---|---|---|
| `assets/processed/ro-swordsman-combo/v004/ro_swordsman_combo.glb`（r001 連段，300 幀） | 25 骨、骨名相同，但手臂 rest 方向差 107–126 度（A-pose 對 T-pose） | 不重定向。`p3-plan-review-01` D2：舊動作不可用，只取時間標記；本次依動作表重新製作 |
| `assets/processed/ro-swordsman-combo-r002/v003/ro_skill_effects.glb`（23 個 FX 物件，2,448 面，300 幀） | 斬擊弧、怒爆地環與火焰、霸體光暈的形狀與材質 | 形狀可參考；時間要配合新連段重打，於 Blender 重建效果層 |
| `scripts/cv1_author_clip.py`（keys 模式、pelvis、legs_ik、sword IK、named poses） | 全部沿用 | 不新增工具 |
| `b20-coatlie3/poses.json` 的 `two_hand_chop`（r6 凍結雙手下劈） | 雙手握劍階段直接用 | 以 weight 漸入漸出 |
| Hyper3D API（餘額 224 點，唯讀查詢 2026-10-07T02:36Z） | 網格生成 | 連段是骨骼動畫、效果層是簡單程序化網格，目前沒有需要生成的輸入；不扣點 |

## 設計

- 從 Idle a03 第 0 幀姿勢出發、第 299 幀回到同一姿勢，讓 `Idle->Combo->Idle` 轉場的 continuity 關卡成立。
- 時間：provoke 10–70、bash 70–135（斬擊事件 112）、magnum_break 135–200（起跳 150、落地重劈 172）、endure 200–255（光效 205 起）、victory 255–299（舉劍 268）。
- 右手全程 grasp.R，劍以 IK 跟手；雙手階段用凍結的 `two_hand_chop`（劍放在其 grip point，隨骨盆高度平移）。
- 腳：`legs_ik` 固定踝點，跨步時抬腳；跳躍期間 IK 關閉、腿部以步進彎曲；stance 時窗依腳著地區間宣告。
- 效果層：另做 `FX_*` 物件（斬擊弧 112–126、地環與火焰 172–200、金色光暈 205–250、勝利光點 268–290），以可見性／縮放動畫，獨立 GLB，可關閉。角色檢查不含效果。

## 步驟與證據

1. `prep/spec-a01-used.py` → `clips/<clip>/clip.json`、`interaction.json`；登錄互動設定（第一次量測前）。
2. `cv1_author_clip.py` → `a01/<clip>.blend` 與 author-report；`cv1_clip_check.py --preview-only` 看 12 個姿勢。
3. `cv1_clip_check.py` 完整檢查（b20 基礎）；依失敗修訂（每個假設最多兩個變體）。
4. `cv1_clip_pipeline.py export/readback`、runtime 閉環；P4 轉場表補 `Idle->Combo->Idle`。
5. 效果層製作與 skill-effects 檢查；美術審查；紀錄與時鐘。

## 製作紀錄（2026-10-07）

- **a01**（`prep/spec-a01-used.py`）：自由階段用劍 IK 指定握點與劍身方向。作者工具先在腿長、手臂可達距離上失敗多次；
  用 `prep/reach-probe-used.py` 逐幀量測後才通過。完整檢查（671 個取樣）：collapse 427、右手自交 560、劍身穿入、握持、腳步皆失敗。
  原因：凍結的 grasp.R 握法讓劍身大致與前臂反向，任意指定劍身方向會迫使手腕彎 90–150 度（契約 60 度）。
  另外量到凍結的 `two_hand_chop` 是「舉劍向上前方 65 度」的雙手架勢，不是下劈。
- **a02**（`prep/spec-a02-used.py`）：自由階段（挑釁、狂擊、勝利）改用右臂 FK 關鍵姿勢（契約詞彙：屈曲、外展、軸轉、肘屈、旋前、腕屈），
  姿勢由 `prep/arm-pose-probe-used.py` 的 7,200 筆 FK 表挑出；劍只在 Idle 兩端與雙手架勢用 IK。
  雙手架勢固定時脊椎歸零，怒爆的「下劈」用全身前傾 55 度把舉起的劍壓到接近水平；握點、傾角與骨盆共用同一組關鍵幀。
  斬擊終點因握法限制只能做成「向右前下方掃出」，與動作表第 6 格有差，記為已知偏差。
- **效果層**：`scripts/cv1_fx_layer.py` 讀取片段的劍路徑產生 25 個 FX 物件（344 面），獨立 GLB，依事件計時；角色檢查不含效果。
- Hyper3D：未使用（餘額 224 點，唯讀查詢）。
- **a03–a07**（同一互動設定，`prep/spec-a0X-used.py`）：
  - a03：放鬆左手握拳與招手彎曲、斬擊手腕改中性、落地下蹲由 0.62 m 改 0.70 m、前傾 55 度改 45 度。
    檢查：握持已通過（a02 失敗是工具 bug：第二個部分權重姿勢把握劍手指重設，已修 `cv1_author_clip.py`）；
    左手自交 400 多個取樣、雙手架勢期間 clavicle.L 折疊。探針（`prep/clip-frame-probe-used.py`）發現原因：
    步進旋轉是加在具名姿勢之後，架勢期間停在 Idle 數值的左臂步進把左手推離劍柄、手指過彎。
  - a04：stance 時窗內腳的朝向不再變化（a03 的 17 mm／10 mm「滑動」來自腳掌繞踝轉動）；斬擊與勝利姿勢再放鬆。
  - a05：架勢期間（156–248）左臂與左手步進全部歸零。探針：手部自交由 53–76 對降到 2 對，剩右腕對護腕 13 對。
  - a06：架勢期間不再用 IK 重解右臂（IK 的 swivel −40 讓手腕彎到 62 度壓進護腕），直接用凍結姿勢的手臂旋轉，劍跟著 hand.R。
    探針：架勢各幀 0 自交、0 新增交叉；唯一 collapse 是凍結姿勢自帶的 28476（面積比 0.047）。
  - a07：勝利握拳再放鬆到 35／45 度（a06 勝利仍有 8 對指間自交）。探針乾淨；完整檢查見 `a07-check-b20/`。
  - a04、a05 的完整檢查在被 a06／a07 取代後中止，資料夾移除，留 `.note`。
- **a07 結案（第 29 筆授權 H1）**：完整檢查 671 取樣，手部、腳步、劍對身體通過；collapse 254（184 為凍結架勢自帶的 28476，面積比 0.047）、握持 3 個過渡取樣失敗，列為已知失敗。
  匯出 `a07/export`（55 個參考區塊、半幀 112.5／172.5／268.5），回讀最大 3.69 µm（門檻 5 µm）通過；runtime 閉環 54 幀最大 6.03 µm（門檻 10 µm）通過，反例全部被抓到（`clips/runtime/20261007t040116z-runtime-results.json`）。
  審查圖 `combo-review-sheet.png`。轉場見 `p4/p4-plan.md` 連段一節。
