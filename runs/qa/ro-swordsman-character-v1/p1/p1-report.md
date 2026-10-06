# 可重用角色動畫 V1：P1 最小閉環報告

時間：2026-10-05，P1 時鐘自 UTC 03:32:29 起，記帳時 788.8 秒（上限 14,400 秒）。P1 不計候選；候選已用 0／4。
授權：使用者「runtime 選 A，預算同意，保護區 A、B 授權，開始 P1」。
結論：**接線關卡通過**。這只證明所選 runtime 能在真實角色上顯示並量測「混合後姿勢驅動的修形」，不是美術、完整動作或交付驗收。

標記：**VERIFIED**＝本次實跑觀測；**INFERRED**＝推論；**UNVERIFIED**＝未驗。

## 1. 驗了什麼

對象是真實完整角色（`ro_whole_baseline.blend`，NO_SHIP 基準，57,039 tri／53 骨），唯讀開啟、未儲存，SHA 前後相同。
沒有修改任何網格、權重、骨或 shape key；只使用既有資料：61 幀骨骼動作、右腕 `WristVolume_025/050/075/100`、手套 `GripContact_R`。

流程：Blender 匯出 GLB → Three.js 0.186.0 載入 → `AnimationMixer` 取樣／混合 → 讀最終骨骼旋轉 → 規則求值寫入 morph → 引擎 morph 後 skin → 逐頂點與 Blender 求值位置比對。

探針規則（`p1-probe-rules.json`）：
- 身體修形：`hand.R` 相對 rest 的旋轉朝「既有 frame 61 姿勢」的進度 p（0–1），以 0.25／0.5／0.75／1.0 的 in-between 權重驅動四個腕部形狀。
- 接觸修形：`GripContact_R` 權重＝互動狀態 `grasp.R`，與姿勢無關。
- 這是接線探針，不是已接受的通用修形。

## 2. 結果（VERIFIED，最終執行 `p1-20261005t034404z`）

門檻在量測前登記於 `phase-start.json`：接線關卡 max ≤ 100 µm；1 µm 為只報告的精度層。
量測量：10 件蒙皮網格全部 33,587 個匯出頂點，經原始 ID 屬性對回 Blender 31,639 個頂點（全部覆蓋）。

| 項目 | 取樣 | 最大誤差 | 超過 100 µm | 超過 1 µm |
|---|---|---|---|---|
| runtime 求值器，整幀（1／16／31／46／61）| 5 | 14.702 µm | 0 | 227 頂點次 |
| runtime 求值器，半幀（8.5／23.5／53.5）| 3 | 12.924 µm | 0 | 121 |
| 兩動作 0.5／0.5 混合 | 1 | 7.567 µm | 0 | 45 |
| 烘焙 clip，整幀 | 5 | 14.702 µm | 0 | 227 |
| 烘焙 clip，半幀 | 3 | 12.924 µm | 0 | 121 |

- p 取到 0／0.125／0.25／0.375／0.5／0.75／0.875／1.0，涵蓋未啟動、部分、完全啟動。
- 驅動值 p 與 Blender 的差 ≤ 3.2e-7；morph 權重差 ≤ 1.3e-6。
- 規則對既有時間曲線的重現：61 個整幀最大差 1.07e-6（門檻 1e-3）。
- rest 姿勢（frame 1）最大 0.827 µm。
- 帶修形的右腕與手套網格最大 0.55 µm；最大誤差都在 `SM_RO_core`。

反例（全部被抓到）：

| 反例 | 結果 |
|---|---|
| NC1 frame 61 關閉求值器 | 最大 18.603 mm，316 頂點超過門檻 |
| NC2 求值器讀到前一取樣的舊姿勢 | 最大 2.963 mm，294 頂點超過門檻 |
| NC3 把烘焙 clip 的 GLB 以 runtime 求值器模式載入 | 擁有權檢查列出 5 個衝突通道 |
| NC4 規則指定不存在的骨 | 拋出 `MISSING_BONE:hand.R_not_in_skeleton`，不會默默當 0 |

圖像：Blender 與 runtime 以同一正交鏡頭各 3 張灰模（frame 1／31／61），另 1 張 runtime 貼圖圖。兩邊輪廓與姿勢一致。這是定性對照，量測值是 CPU 求值，不是 GPU 畫面的像素證據。

## 3. 過程中的失敗（保留）

第一次量測 `p1-20261005t034147z` **未通過**：最大 32.319 mm。分類 TEST_FAILURE。
原因：量測程式假設 frame f 的時間是 (f−1)/fps；實際匯出的 clip 把 frame f 放在 f/fps（最早 1/60 秒、最晚 61/60 秒），所以每個取樣都早了一幀。
依據：frame 1 誤差只有 0.83 µm、驅動值差恰為 1/60、runtime 與烘焙兩種模式誤差相同、直接讀 GLB accessor 的 min／max。
處理：只改量測程式的時間對應，並加上「key 時間不符就拒絕執行」的檢查。預先登記的取樣、門檻、規則、GLB 與 Blender 參考都沒改。紀錄在 `runtime-attempt1-failure.json`。
`blender-reference.json` 內的 `time_s` 與 `frame_to_time` 標籤仍是舊的錯誤寫法；它們不被讀取，維持原樣未改寫。

第二次 `p1-20261005t034255z` 通過。之後只改了頁面的著色與參考點疊圖、並讓結果記錄量測程式雜湊，再跑第三次，數值相同。

## 4. P1 得到的接入事實（已寫入需求草稿 `runtime_contract_draft.p1_verified_20261005`）

| 事實 | 層級 | 對後續的影響 |
|---|---|---|
| 求值順序可行：混合 → 最終姿勢 → 規則 → morph → skin | VERIFIED（混合取樣＋NC2）| 通用修形求值器照此順序實作 |
| glTF 節點 local 旋轉＝Blender 骨骼 rest-relative local 旋轉 | VERIFIED（驅動值差 ≤ 3.2e-7）| 規則的目標四元數可跨兩端共用 |
| GLTFLoader 會移除名稱中的 `.`（`hand.R`→`handR`）| VERIFIED | 骨對應必須用 `userData.name` 的原名 |
| clip 時間原點是 frame/fps，開頭有 1/fps 靜止段 | VERIFIED | P3 凍結前要決定 slide-to-zero 或記錄 lead-in，否則 loop 有停頓 |
| 匯出器略去 ≤ 1e-4 的權重 | 最差頂點 core#6637 帶 `clavicle.R` 權重 8.69e-5，core 共 333 個此類頂點：VERIFIED；殘差由此造成：INFERRED | 1 µm 回讀門檻目前未達；交付前要把 r010 的精確權重還原方法參數化 |
| 每通道唯一 owner 可檢查 | VERIFIED（NC3）| runtime-owner 與 baked-owner 分成兩個檔 |

## 5. 沒有證明的事

- 沒有任何美術改善；腕部與握持的既有缺陷原樣存在。
- 只有 8 個取樣加 1 個混合；不是連續時間保證。
- 只測了一條旋轉差規則與一個狀態驅動；多關節組合、錐形／RBF 類驅動未設計。
- 沒有 IK／手勢層；「IK 之後再求值」的順序只以動畫混合代表，尚未實測 IK。
- 沒有性能量測；量測全程約 5.2 秒是 CPU 逐頂點比對的時間，不是幀時間。
- GPU 實際畫面沒有做像素級比對。
- 新骨架、左手（保護區 A、B）尚未動工；P2 起才開始，且會計入候選。
- Godot、Unity、changshan-longdan 遊戲皆未驗。
- QA 頁目前只有 P1 需要的操作（owner 切換、seek、播放／暫停、速度、求值器開關、grasp、鏡頭、材質、參考點）；轉場、多動作切換屬 P4。

## 6. 重跑方式

```powershell
# Blender 參考與 GLB（輸出已存在時會拒絕覆寫）
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --factory-startup --disable-autoexec assets/processed/ro-swordsman-combo-r010/baseline/ro_whole_baseline.blend --python scripts/cv1_p1_export_reference.py
# 相依套件與 QA 頁
npm install --ignore-scripts --prefix tools/runtime-qa/three
python -B tools/runtime-qa/three/serve.py --port 8765
# 瀏覽器開 http://localhost:8765/ ，按「執行 P1 量測並存檔」
python -B -m unittest discover -s tests -v
```

## 7. 檔案

| 位置 | 內容 |
|---|---|
| `assets/processed/ro-swordsman-character-v1/p1-closed-loop/` | `ro_character_p1_runtime_owner.glb`（35,162,952 bytes，clip 只有骨骼）、`ro_character_p1_baked_owner.glb`（2,459,148 bytes，含 morph 軌、不含貼圖）、`p1-probe-rules.json` |
| `runs/qa/ro-swordsman-character-v1/p1/phase-start.json` | 量測前登記的取樣、規則、門檻、反例 |
| `…/blender-reference.json`、`.f64.bin` | Blender 求值位置（17 個區塊）與匯出設定 |
| `…/blender-wrist-frame-001/031/061.png` | Blender 灰模 |
| `…/runtime/p1-20261005t034404z-*` | 最終 runtime 結果與 4 張圖；`034147z`（失敗）與 `034255z` 亦保留 |
| `…/runtime-attempt1-failure.json` | 第一次失敗的分類與修正 |
| `…/authorization-envelope-npm-three.json` | 下載範圍紀錄 |
| `…/p1-accounting.json` | 時間、候選、39 個檔案的 SHA-256 |
| `scripts/cv1_pose_rules.py`、`tools/runtime-qa/three/src/cv1-pose-rules.js` | 規則求值（Python／JS 兩份，單元測試核對一致）|
| `scripts/cv1_p1_export_reference.py` | 匯出與參考腳本 |
| `tools/runtime-qa/three/` | QA 頁、本機伺服器、`package.json`／lock（`node_modules` 不進版控）|
| `tests/test_cv1_pose_rules.py` | 9 項新測試 |

本次檢查：單元測試 140 項 OK（原 131＋新 9）；`pipeline.py validate` exit 0；需求 `validate` 為 `valid_request`；`git diff --check` exit 0；r010 歷史 311 筆重算不一致 0；HEAD `c990639` 未變、staged 0。
新增 API 提交 0、點數 0。下載只有 `three@0.186.0`（lock integrity 與 registry 一致）。
worktree 以外的寫入：`C:\Repos\mmo-asset-pipeline\.claude\launch.json`（預覽伺服器啟動設定，新增的未追蹤檔）。
