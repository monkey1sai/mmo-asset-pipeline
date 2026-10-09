# D1 第二候選與停止條件 checkpoint

日期：2026-10-09，Asia/Taipei。狀態：NOT_COMPLETED；整體 spec **1/6**，game_ready=false。

沿用 [最終驗收增補](mixamo-secondary-acceptance-20261008.md)。本次使用者核准額外 3600 秒，於 2026-10-08T22:23:43Z 開始；不重置歷史時間、候選數或 E12 預算。累計上限仍為兩個候選，兩個均 FAIL。沒有第三候選授權。

## 實際製作

獨立審查接受有限衣料面板試驗：原始 496 頂點／812 面，212 個接縫與邊界頂點固定，只修改 284 個內部頂點。308 個外部接縫鄰居含其他衣物，排除。這不是完整披風語義遮罩。

直接重用 `scripts/weight_vector_solver.py`：600 次 Jacobi、relaxation=0.7、fidelity=0、逆邊長權重，距離下限 1µm；輸出截為四個骨影響並正規化。既有稀疏 GLB patch 工具保證僅授權配重欄位改變，幾何、材質、UV、骨架與武器介面不變。原始 GLB 未覆寫。

來源核對第一次在模型寫入前失敗。查證骨名與索引完全相同，診斷快照與 GLB 配重最大差異為 1.1920928955078125e-7，最多兩個 FLOAT32 ULP。續跑保存原試驗開始時間，以原始／候選 GLB 的實際序列化配重計算 CPU 形變，沒有重新計數。此差異不足以證明唯一根因。

候選 SHA-256：`79fd409c69433fc331d5387d0ef34f7c3e8a5c330f00c3e2035b69eb1fdb4a6a`。僅 4838 bytes 改變；授權區外位元組完全相同。

## 結果

| CPU 階段 | baseline 異常邊 | candidate 異常邊 | 新增／消除 |
|---|---:|---:|---:|
| fresh import | 0 | 0 | 0／0 |
| bind-only | 0 | 0 | 0／0 |
| idle once | 3376 | 3405 | 80／51 |
| idle 2 seconds | 3380 | 3415 | 91／56 |

171 是兩個 idle 階段新增邊數的合計，不是跨階段去重數。固定接縫距離沒有新增退步。種子邊在 idle 由約 0.478m 降至 0.0516m，但內部新增拉伸使整體 **FAIL**。不能以種子改善抵銷其他退步。

求解器收斂不代表配重可接受；四影響截斷後與完整解的最大 L1 差為 0.7459439558。這是需要另行查證的退步線索，沒有在本試驗改參數重跑。

Blender 5.2.2 LTS 全新重匯入 baseline／candidate，固定相機與光照，保存 12 張圖及失敗場景。rest、右臂 15°、右腿 30°、披風 30°共八組 CPU／Blender 對照全部 PASS，最大頂點誤差 2.711714737e-7m。單骨旋轉的異常數部分下降，但完整 idle CPU 退步；已檢視腿部與披風壓力圖，仍可見尖三角及破碎部位，角色美術 **FAIL**。不是自然動態驗收。

本地美術工作樹工程檢查：369 Python tests PASS、0 skipped；pipeline validate PASS（39 assets／11 operations，僅 schema／清單／ledger）。本 checkpoint 未修改核心程式；main 在先前 PR11–16 合併後另驗 364 tests PASS、0 skipped。兩份工作樹測試範圍不同，不能宣稱所有本地工具已合併 main。

## 可定位的本地證據

以下相對於保留的美術隔離工作樹 `tmp/mixamo-secondary-20261008`；未公開完整圖像、GLB、Blender 場景或原始快照，再散布權尚未確認。

- `requests/cl-zhaoyun-secondary-v003.json`：新預算版本，canonical SHA-256 `c006ede56a8f58d3be7bc4662b2883b8d711cd8b1dd8249280b3254609aac091`。
- `runs/qa/zhaoyun-d1-authorized-extension-v003.json`：授權與時計。
- `runs/qa/zhaoyun-d1-seam-context-v003/`：範圍、九張上下文圖。
- `assets/processed/zhaoyun-d1-local/v002/`：frozen、source-correlation、patch-profile、solver-report、完整 cpu-report、失敗 GLB。
- `runs/qa/zhaoyun-d1-pressure-v002/`：重匯入、同版壓力圖、失敗場景及量測。衍生報告的舊 `cpu_hypothesis` 標籤沿用第一候選字樣；本候選實際為新增內部異常、接縫無新增退步，以本文件與 CPU 逐邊紀錄解讀。
- `runs/qa/zhaoyun-d1-weight-prototype-v002.log` 與 `...-retry-v001.log`：初次 preflight 失敗及同時計續跑。
- `runs/qa/zhaoyun-d1-extension-tests-v003.log`：本輪工程測試。

CPU report 原始檔 SHA-256：`18c6ec551052e21f12bea70d771486b8699721fefa9e1e736392d15413726b57`；DCC report：`2bdea370dc7811ddb8205770819b71aa12c517379f5418a9a041dc17ab8ca2ff`。本地交付補充包 `deliveries/cl-zhaoyun-secondary-v001/v003/manifest.json` 保存 56 個檔案、42,244,041 bytes，全部雜湊回讀 PASS；manifest SHA-256：`c74aa460410184e28d2f1b199dedb570f9fe1e3cacf954adc0a61a7fa538df15`。此為失敗證據補充包，依賴既有 v002 交付與完整 repo，package_complete=false，不是完整成品。

## spec 完成度與下一步

| 階段 | 狀態 |
|---|---|
| D0 診斷 | PASS，已有結案 checkpoint |
| D1 修復 | FAIL／未完成，兩個候選均未採用 |
| D2 製作路線 | 未完成；完整部位與身體整理仍缺 |
| D3 Mixamo | NOT_RUN；沒有合格中性副本或真實來源動作 |
| D4 製作端接受 | 未完成；部分共用工具僅本地，真實角色未接受 |
| D5 Unity 完整遊戲 | NOT_RUN；原版引擎基礎測試 PASS、角色視覺 FAIL，不能替代候選驗收 |

停止本輪候選製作，保存第一、第二 FAIL 及來源。回滾方式為不採用候選，繼續使用未改寫的原資產；不刪歷史或 reset dirty 工作樹。下一個必要決策是先人工修正衣料語義邊界與跨部位固定配重，評估最小拓樸修整，再提出新的一個具體製作試驗；須重新界定候選預算，不能在剩餘時間偷偷建立第三候選。

Mixamo 上傳仍須逐次核對副本、權利與外傳授权；Hyper3D 仍須確認月訂分項。未修改 target rig、遊戲 runtime、E12 量測器，未進行外部素材上傳或付費生成。只有同一接受候選完成 Unity 的走跑跳、轉向、攻擊、格擋、閃避、無雙及人類視覺審查，D5 才可 PASS，整體才可 COMPLETE。
