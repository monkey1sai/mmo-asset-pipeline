**已完成 r010 最終唯讀審查。現有實物、程式與保存紀錄支持「局部數值技術驗證通過」；本次未發現阻斷該限定結論的實際缺陷。包握美術、UV、全角色與完整 300 幀仍不能列為通過。** 將本階段記為 `local_technical_pass`，同時維持完整品質 `failed / not_ready / stop_budget`、原品質分數不變，是符合證據的收束方式。本報告為獨立審查意見，不是人類批准。

**Scope／做法與理由**

本次直接讀取 fresh GLB attempt 3 的結果、逐時間點紀錄、原契約、權重還原驗證及相關腳本，查看 corrected palm／side 與兩張 wireframe。另以唯讀命令重新彙總 121 筆事件、1,106 筆權重對應紀錄，核對最終 GLB 與 v003／v004 BLEND 的實際 SHA-256。未執行 Blender、產製腳本、API、Git 或任何寫入。

**VERIFIED：可成立的局部技術結果**

1. **最終檔案確實對應受測成果。**
   [fresh GLB result.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r010/v004-fresh-glb-attempt3/result.json) 綁定的最終檔案為：

   `assets/processed/ro-swordsman-combo-r010/v004-certified-animation/right_hand_grasp_61f_exact_weights.glb`

   本次重新計算其 SHA-256，與報告一致：
   `54c27c256e4b06a2312a8d0562e68195a64a5b502b21e23a5d0d3c453d773502`

   v003 原動畫與 v004 保存 BLEND 的實際雜湊相同，皆為 `a0167656…131c96`。因此 v004 的分類修正沒有被混充成形體改善。

2. **121 個受測時間點全部符合保存的數值門檻。**
   本次重新彙總 `v004-fresh-glb-attempt3/interval-events.jsonl`：第 1 至 61 幀、含半幀，共 121 筆，失敗 0；其中第 31 至 61 幀共 61 筆要求接觸，五指各至少 3 點。所有樣本的已測自交／劍橫向交叉、採樣穿入深度及剩餘 unknown 都為 0。

   保存結果中的最大手部同 ID 差為 **1.9385832297e-7 m**、RMS **4.1020052043e-8 m**；武器點差最大 **1.9082797281e-7 m**，骨骼跟隨誤差最大 **1.5359765387e-7 m**，均低於原 **1e-6 m** 容差。這些是已保存實跑結果，本審查沒有另啟 Blender 重測。

3. **fresh GLB 的量測方式可接受。**
   [verify_ro_fresh_grasp_glb.py](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/scripts/verify_ro_fresh_grasp_glb.py:27) 依匯出的原始 ID 合併 UV／法線分裂頂點，不做空間 nearest 配對、不平均、不作 posed weld；每個時間點重新取得求值位置與三角形，檢查對應、碰撞、接觸、邊長及武器跟隨。實測分裂副本位置差最大為 0。

   第 79–80 行保留原交叉、unknown、深度、邊長與位置容差條件。新 GLB 的功能結果是重新計算所得，並非承接前一次失敗匯出的 PASS。

4. **權重修復的範圍與證據充分。**
   [exact-weights-verification.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r010/v004-certified-animation/exact-weights-verification.json) 記錄實際 body node → mesh → primitive → skin 映射、accessor 布局與 joint 容量檢查。
   `verify_ro_glb_exact_weights.py` 第 120 行逐列要求還原權重等於凍結來源，第 131 行限定二進位差异只能位於允許的 JOINTS／WEIGHTS byte ranges。

   本次另行彙總 `exact-weights-all-IDs.json`，確有 **1,106 列／904 個原 ID**，還原後最大 L1 為 **0**，修復前最大為 **0.00019625548884505406**。驗證報告記錄原先遺漏 **109 個來源影響項**、實際僅 **1,686 個允許位置的 bytes** 改變，並保留單一動畫、52 channels。這支持「還原來源權重」的結論，沒有顯示重新設計權重或形體。

5. **射線補充分類沒有放寬 unknown 門檻。**
   `ro_certified_grasp_gate.py` 僅補充 `parity_unknown`，保留原報告；判為 inside 時仍累計穿入深度。`ro_solid_angle.py` 已在相減前轉成 float64，採 exact coincident position 對應，不用座標量化封口；未閉合、方向不一致、退化及非有限表面會拒絕。

   `classification-preflight.json` 保存實際劍的一個 2,552 面連通件、零位置差接縫、平移／旋轉／鏡射及已知 inside／outside 交叉核對。fresh 第 46.5 幀保留原 unknown 1，再以 winding **−5.5217963e-18** 分類為 outside，剩餘 unknown 0。這是量測方法修復，不是模型品質提升。

**INFERRED：不能宣稱包握美術 PASS**

我實際查看了：

- `v003-index-pulp/corrected-palm.png`
- `v003-index-pulp/corrected-side.png`
- `v003-index-pulp/wireframe-palm.png`
- `v003-index-pulp/wireframe-side.png`

圖片沒有顯示 corrective 把三個測量點拉成孤立尖刺；線框中的形變分布也比單點拉近合理。但側面仍呈較鬆的 C 形環繞，指節轉折偏硬，指腹與掌心尚未形成有說服力的握柄支撐關係。掌面可見四指末端靠近柄的輪廓，但**每指三個頂點在 2 mm 內，只能證明既定 proximity gate，不能證明接觸面積、對掌受力或自然包握**。

因此，可保存本次數值功能改善，不能將它寫成獨立灰模美術驗收已通過。契約中包含 `independentgrayshapeacceptance`，所以 `local_technical_pass` 必須明確指數值／匯出子項，不能作為整個 `functional_gate` 已全面通過的別名。

**UNVERIFIED／必要限制**

- 121 個時間點是離散採樣；不能宣稱連續時間內任意時刻均有數學保證。
- 自交方法明示排除相鄰面、相切及共面折疊；零橫向交叉不等於不存在所有視覺折疊。
- 穿入深度是既定點／邊／面採樣方法的結果，不是連續表面最大深度的精確證明。
- `certify_oriented_closed` 檢查閉合、定向及體積，沒有完整的劍自身三角形自交驗證。它足以支持本次固定來源與遠離表面的歧義點處理，不應被宣傳為任意網格的實體有效性認證器。
- UV／材質問題、全角色配裝、完整 300 幀與獨立 VFX、目標引擎均不在這次通過範圍。本次也未驗證遊戲 runtime。

**停下與下一步**

沒有需要新增候選或改動模型才能成立的局部數值結論。協調者可完成第四候選與本階段封存，保留前述所有失敗及測試修復紀錄，使用明確的結論：

> 局部 61 幀動畫在 121 個指定時間點的數值門檻與 fresh GLB 一致性通過；包握美術及完整需求未通過，整體仍 not_ready，四候選預算用盡。

封存索引應直接綁定 `right_hand_grasp_61f_exact_weights.glb` 和 attempt 3 結果。早期 `v004-certified-animation/result.json` 仍指向最初 GLB 且寫有 `freshGLB: pending`，這是應保存的歷史階段紀錄；最終 README／registry 必須標明後續有效成果，避免讀者誤取舊檔，無須回寫抹除歷史。

無待人類決定事項。本審查已完成，目前沒有背景工作繼續執行。
