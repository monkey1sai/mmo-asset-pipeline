# 角色續作結果：未完成，唯一候選驗證失敗

使用者選項 1 的授權已執行：新獨立階段最多 2 小時、1 個候選，舊時計／耗用／失敗與原門檻保留。本次候選額度 1/1 已用完，未消耗付費點數、未 commit/push、未改其他 repo 或原角色。

## 結果與證據

| 檢查 | 實際結果 |
|---|---|
| 新 baseline 完整 P4 | **FAIL**：116/118，max 18.731347653251667 µm |
| 唯一候選完整 P4 | **FAIL**：116/118，max 19.08394124832543 µm |
| 原 10 µm gate | 保留，未放寬 |
| 其他 7 verdict／4 negative controls | 兩次均 PASS／detected；不能抵銷閉環失敗 |
| 候選 helper Node tests | **PASS**：4/4，未 skip |
| 隔離角色來源 Python suite | **PASS**：306 tests，未 skip/fail；與另一工具 worktree 的 314 tests 範圍不同 |
| catalog validate | **PASS**：39 assets、11 operations；不是 runtime／藝術／delivery 驗證 |
| protected inputs | **PASS**：47 份 current/original SHA 核對；含 foundation、references、clips、fixtures、contracts、Blender scripts |
| 最终独立 review | **reject**：failed/discard，詳 `independent-review.md` |
| runtime baseline 恢復 | **PASS**：p4.js SHA 回到 8b661c…，無採用候選程式 |
| gait 自然度／P5／角色交付／遊戲接入 | **NOT_RUN／未完成**：不能在本輪追加第二候選 |
| remote CI | **NOT_RUN**：沒有本輪 commit/push |

Baseline run：`20261007t100753z`；候選 run：`20261007t101631z`。完整 JSON 含所有 118 blocks、harness SHA、GLB／reference SHA、硬體／Chrome／WebGL、negative controls 及原 gate。執行是 **headless background local P4 harness**，不是可見遊戲玩家驗收或 release PASS。

## 有效診斷與未解問題

同一 Combo296／Idle3、50:50、雙足鎖定姿勢的 core ID5297，兩端 base/morph/非零 bone weights 一致；差異從 skin 變換鏈開始。相同 solver 輸入下 Python/JS two-bone 結果一致；實際足鎖前輸入相差低於 1 µm，但近伸直 IK 放大了差異。

讀取原 inverse-bind 還原 rest affine，腿部 rest 矩陣最大元素差異由 TRS 約 3.8e-6 降至約 9.4e-8。118 reference pre-IK 姿勢的 1,180 取樣點：max 1.7478→1.1830 µm、RMS .5537→.4294 µm；725 點改善。這只證明局部輸入更接近，沒有證明最終 skin 改善。

唯一候選不按 clip/幀號/vertex ID 特判，只讓 foot-lock FK 使用原 inverse-bind rest affine。完整回歸仍失敗，max 退步約 .352594 µm，超標匯出頂點每筆 1751→1759。因此 **discard，維持原 baseline 的真實 FAIL**，不改 reference、不調 epsilon、不動 source rest、weights 或 morph。

下輪待驗假設：比較 IK 前後完整姿勢表示，包含 affine FK 位置、world rotation 抽取、parent inverse／bone basis 寫回與最後 skin 鏈。候選位置轉成 affine，但旋轉／寫回仍是 rendered TRS；目前不能宣稱修這一段就會通過。

## 保存與恢復

`candidate-01.json` 保存授權、假設、FAIL、discard、範圍與剩餘候選為零。完整已測 source 在 `candidate-01-source/manifest.json` 指向的三個檔案，含當時的路徑與 SHA；`p4.js`／helper 的 SHA 與候選 run 相符。正式 runtime 路徑已恢復 baseline，archive 不會自動啟用。

原 92f8 gait worktree 在本輪已不可讀；歷史盤點提到的 ab-plan-v002 並不等於現在已有可讀凍結檔。自然度續作需先恢復該交接實物、核對 SHA 和來源准入。本輪沒有重建或假稱已恢復該 A/B 契約。

準備失敗保留：第一次 Blender 診斷誤用了早期 p2 contract，`KeyError: 'excluded_meshes'`，改用 run-07 記錄的 r4/v5 contract 後成功；connector 缺 Playwright extension 為 ENVIRONMENT_FAILURE，沿用已安裝本機 runner；第一次自動化 click acknowledgement timeout 為 TOOL_FAILURE，未產生完整 baseline，改用非阻塞事件 dispatch 後全量成功。這些未當成 PASS、未重置角色預算。

本輪因 1/1 候選已用完而停止試作，無須耗滿 2 小時。無新增待批准的遠端操作；P4 技術阻礙、gait、P5 與完整角色交付仍未完成，需要另一次明確有界續作範圍才能新增角色候選。
