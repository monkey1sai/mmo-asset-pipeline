# 趙雲工作流 D0 診斷 checkpoint

日期：2026-10-08。Spec：`mixamo-secondary-character-workflow-v1`。本文件是診斷摘要，未包含模型、貼圖、動畫或原始幾何快照。驗收增補見同 repo PR #11；它尚未合併，這份摘要不宣稱已進 main。

## 結果與完成度

D0 本地確定性結案稽核與獨立階段審查 PASS，正式完成度 1/6。真實趙雲形變與視覺仍 FAIL。D1 修復候選、D2 製作路線、D3 Mixamo、D4 製作端接受、D5 Unity 遊戲接受未完成。獨立審查重算 43 項 actual SHA-256 一致；此判定不是 counted human approval。

原 GLB SHA-256 `7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33` 已重新核對，來源未修改。共用程式以 CLI 參數指定來源、雜湊、mesh 與輸出，不寫死趙雲、遊戲或絕對路徑。

## D0 證據與判定

| 條件 | 本地結果與範圍 |
|---|---|
| 原始 ID／三角形 | 27,815 個原始頂點 ID 明確對應，三角 multiset 一致 |
| 配重不變性 | 最大差 1.19209e-7，符合 1e-5 門檻 |
| evaluated bind | GLB 實際 fresh skin 與 Blender evaluated bind 最大差 0.316µm，PASS；raw import co 的舊 FAIL 保留，兩種對象不同 |
| 骨階層探針 | baseline、右臂、右腿、披風、右臂親子五組 CPU／Blender parity 全部 PASS；非 baseline 有真實拉伸 FAIL |
| baseline 回讀 | 保存的 .blend geometry／normal／UV、材質 bindings、hierarchy／rest PASS；不包含 shader pixels 或 runtime |
| 實物與歷史證據 | D0 與 r005 manifests 所列診斷實物 hashes 已重核；舊 spec hash 因新授權版本而不一致，v001 audit FAIL 保留，v002 明示精確新 authority |

本地稽核 run：`runs/qa/zhaoyun-d0-closure-v002.json`；原權威 spec SHA-256 `465bfa9f31461896bd9579099a91e814fb859b179d84ca928fe36786d2852157`。以上是已有診斷成果的重新核對，不改寫舊 log 或重算歷史預算。

## 部位判定進度

新增 `scripts/blender_component_review.py`，組合既有 `inspect_ro_batch_source.py::components`、identity／art_sources 路徑與雜湊保護，分開輸出精確索引連通區與 1e-6 mesh-local 量化邏輯焊接連通區。量化不保證是公尺距離；report 記錄 scene unit scale 與 mesh world matrix。邏輯焊接只用於診斷，來源 vertices／UV 不修改；它可能把相接的不同表面合在一起，不能當成解剖分件或修復。polygon indices 為 Blender 匯入索引，未冒稱為原 GLB 三角 ID。

真實 baseline 執行結果：3,752 個索引連通區、8 個邏輯焊接區；最大邏輯區包含 27,046 個三角形。前／後視角已檢視，身體、披風與頭髮在最大區域同色，因此拒絕用它直接產生語義部位遮罩。連通診斷不能單獨證明融合／錯接拓撲，也不能放行自動拆件或配重。

新增 review .blend 只在複製 mesh 上著色，原 baseline SHA 未變；原材料、UV、骨架及權重保留。它是診斷畫面，不是修復候選或 Mixamo 上傳副本。

操作入口（從 repo 根目錄執行；替換為自己的已核對 ID baseline）：

```powershell
& <Blender.exe> --background --factory-startup --disable-autoexec --python-exit-code 2 --python scripts/blender_component_review.py -- --blend runs/qa/<case>/indexed-review-baseline.blend --sha256 <SHA256> --mesh <mesh-name> --out runs/qa/<new-review-id>
```

結果含前／後／側圖、component-review.blend 與 report.json。原始 ID 為 baseline 中的 `original_gltf_vertex_id` 屬性。新輸出不得覆寫舊 review。實際 baseline 是本地受權利保護資料，未附於公開 PR。

## 本輪驗證

- Blender 5.2.2 LTS 正面實跑：v001 與修正欄位標示的 v002 完成三視角、報告與新 .blend，退出 0；baseline unchanged=true。v001 的 original_triangle_ids／tolerance_m 欄位不作原 GLB 面序／公尺主張，以 v002 的 imported_polygon_indices／mesh-local quantization 為準，歷史報告保留。
- 負面／邊界實跑：錯誤 source digest 拒絕 `BASELINE_DRIFT`、輸出到 docs 拒絕 `OUTPUT_SCOPE`，均預期退出 2，測試 harness PASS。
- 本地美術隔離樹：`python -B -m unittest discover -s tests -v`，344 tests PASS；`python -B scripts/pipeline.py validate` PASS。測試數是該本地樹，不能冒充目前遠端 main 或新 PR CI 的 suite。
- 此新增 Blender wrapper 的正負面證據来自本地 Blender 實跑；一般 CI 沒有 Blender，不能把 CI 成功稱為 DCC 重驗。
- 本輪未修改權重／拓撲／骨架，無 Hyper3D 扣點、無 Mixamo 上傳、无 Unity 執行，未釋出 trial 或重設時間。

## 下一步與回滾

D1 仍缺可接受的幾何語義遮罩與可信的剩餘 trial／time 核對。先局部定位與單一修復假設，再建立新候選、固定條件對照；禁止全域平滑掩蓋錯接。Mixamo 副本及外傳另按原規則逐次授權。

回滾只撤回本 checkpoint 的程式與摘要提交；不刪本地原始／失敗／歷史證據，不覆寫遊戲原 GLB。診斷完成不代表 game_ready；整體 spec 只有 D0–D5 結案與同版 Unity 全必要測試及視覺接受後才完成。
