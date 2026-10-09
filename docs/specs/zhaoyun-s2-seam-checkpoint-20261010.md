# S2 REST 接縫與混入表面 checkpoint

依 [執行步驟](mixamo-secondary-execution-steps-20261009.md) 接續 S2，不修改 D0–D5 的完成條件。使用者要求「開始 SPEC」並授權續行。PR18 已合併至 main `c848cbe4b72f950414df54b93bc311d0401ce1b3`；本輪僅做本地唯讀診斷，沒有第三個角色候選、上傳或付費提交。完整 spec 仍 **1/6、NOT_COMPLETED**。

## 已執行與觀察

沿用既有原始 ID、接縫範圍與隔離 Blender 5.2.2 LTS session，對 mesh 複製品移除 modifier，檢視 raw REST 幾何。panel 812 面與 neighbor 274 面各自及合併後，以 front／back／side／under 固定相機產生 12 張圖，均已實際檢視。原始 GLB 與診斷 baseline blend 前後 SHA 相同。載入 baseline 原為 POSE、17 個 matrix_basis 非 identity；此為來源狀態紀錄，不作根因結論，且本輪不保存 blend。

347 對重合點在原始資料的距離均為 0m，配重 L1 差均為 0。這否定此組「原始重合點兩側配重不同」的假設，仍不能排除表面內部錯誤配重。66 對 incident face 的最小法線夾角大於 60 度；法線、UV 或顏色不能單獨決定部位語義。

union 圖可見白色內層鄰居混入綠色表面。從前視圖手動定位畫面區域，投影回原始面 ID，另渲染近看材質／識別色 front、back、under 共 6 張並實際比對，得到：

| 分類 | 原始 face ID | 意義 |
|---|---|---|
| 排除於白色內層面板 | 22105、22106、22673、22679 | 可見綠色鄰接表面；不能納入白色面板修復遮罩 |
| 可觀察為白色鄰居 | 22674、22676、24449、24450、24451 | 僅表面識別；固定配重／真正接縫關係尚未接受 |
| 未確定 | 22680 | 細小接合面部分遮蔽，保留未確定 |

這是局部排除證據，不是接受整個 496 頂點、812 面或 308 個外部鄰居的修改範圍。沒有刪面、修改配重、拓樸、骨架、UV、材質或武器介面。

## 可定位的本地證據

相對路徑以既有本地製作 worktree 為根。本公開 checkpoint 只保存方法、數據與 hash；原始素材、影像及完整幾何資料的公開再散布權仍未確立，不放入此 PR。

| 檔案 | SHA-256 |
|---|---|
| 原始 `zhaoyun.glb` | `7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33` |
| `runs/qa/zhaoyun-s2-seam-review-v002/report.json` | `ce47eab508911f06af2b8caaa3df66c278da64b9c390c2ff4d3b238087fffddc` |
| 同目錄 `front-face-projection.json` | `0780f4a813c1f585c29687eaf28fbeac4477c37f8a0411222f81f8da72bd4df6` |
| `runs/qa/zhaoyun-s2-neighbor-detail-v001/report.json` | `369a403fa44d2e997291ea6e0819de9498f8879e17253cc9efca8b85c903c85c` |
| 同目錄 `semantic-review.json` | `47fd0df7c401589949609be58a25c4864cbff13ef3b111847e909bee9ea24fb9` |
| `runs/qa/zhaoyun-s2-engineering-tests-v001.log` | `8ce1e82694ead6cc8af6a08d670aa0ccaca4cd64cccf34838f6ac710550a5c42` |
| `deliveries/cl-zhaoyun-secondary-v001/v006/manifest.json` | `83e771f1cf6676508a9f2e7b2340383e5e56e169e9f0eb5dc96d9c1361177d5b` |

本地 v006 補充包保留 v005 的原始 bytes，再加入本輪 18 張圖、報告、操作腳本與測試 log：46 檔、20,010,971 bytes，全部 SHA 回讀 PASS。依賴既有 repo 與交付包，`package_complete=false`、`game_ready=false`。不是修復成品或可獨立執行的 Unity 資產。

操作腳本位於 `runs/evidence/zhaoyun-s2-seam-review-v002.py`、`zhaoyun-s2-project-faces-v001.py`、`zhaoyun-s2-neighbor-detail-v001.py`，皆封存於本地包。Blender 使用 `--background --factory-startup --disable-autoexec --python-exit-code 2`；來源雜湊核對與獨占輸出避免覆寫。它們是案例診斷腳本，不是新的核心 pipeline。

## 驗證與下一步

本輪重新執行 `python -B -m unittest discover -s tests -v`：**379 tests PASS、0 skipped**，10.159 秒。`python -B scripts/pipeline.py validate`：PASS，39 assets／11 operations，只驗 schema／catalog／ledger。執行工作樹 head `9dbd5c835e1a61b33d0bc10a1346953a71e7a420` 與 main 的工程程式相同，差異僅 Git 流程文件。這些檢查不替代美術接受或 Unity 測試。

S2 仍 PARTIAL：剩餘接縫、肩背固定、22680 與完整角色分區尚待確認。S3 舊兩候選均 FAIL、既有上限已耗盡；續行不重設舊時計／候選，新的修復範圍與預算須明確版本化。Mixamo 實際整合、真實角色次級動態、Unity 完整遊戲驗收仍未完成。下一步先解析剩餘接縫與固定區，再提出一個局部且可驗證的修復計畫。回滾為不採用候選、保留原資產；不刪失敗證據。
