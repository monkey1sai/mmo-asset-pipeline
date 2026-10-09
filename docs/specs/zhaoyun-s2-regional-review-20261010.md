# S2 肩背隔離與全身區域審查

Task：`S2-root-and-regional-review`。依使用者「一個 task 一個 PR，commit／push／開 PR／auto merge，直到 SPEC 任務完成」續行；沿用 [執行步驟](mixamo-secondary-execution-steps-20261009.md) 及 [上輪掛點定位](zhaoyun-s2-anchor-checkpoint-20261010.md)。起點 main `bb26aedd8cd8b39070cbd6c0c6ae1db9bd2fc265` 的 CI run `37970944154` SUCCESS。本輪未修改核心或角色資產。

遠端查詢 `autoMergeAllowed=false`、`mergeCommitAllowed=true`。不修改倉庫設定或 protection；同 head CI、完整 diff、未解問題與最新 base 核對後，由代理執行普通 exact-head merge。這是 Git 續行授權，不改來源外傳、付費或修復候選額度。

## 實際製作與觀察

沿用已驗證原始 ID、面片索引、材質及 Blender 安全預覽方法，兩次獨立 Blender 5.2.2 LTS 唯讀 session 共產生並檢視 **36 張新圖**。原 GLB 與 baseline blend 前後 hash 不變。根部隔離耗時 24.480 秒，區域覆蓋 21.151 秒，各自在既有 1200 秒診斷上限內；不是修復 trial，沒有重設舊預算。

根部球域的 1391 面來自 **153 個 exact connected components**。本輪以 front／back／right／left 隔離四個主要塊：131（493 頂點／772 面）、2（2271／4017）、418（96／141）、174（121／192），共 16 圖。可見 131 包含胸腰甲及延伸手臂表面，不能整塊當披風；2 為大片背部垂布及延伸表面，含 20 種非零骨頭影響，不能將整塊配重歸給披風；174 可見背部白色布片，418 的獨立衣物身分仍未確認。孔洞可能由隔離其他相接面造成，不能直接認定原模型裂開。

另作 whole、hair-head、waist-skirt、boots、arms 各四視角，共 20 圖。區域只是 world-space 裁切，保留原始 face／vertex ID，不是語義遮罩。

| 部位 | 實際觀察與決策 |
|---|---|
| 身體／肩髖 | 原模型為動作站姿；肩甲及衣料遮住關節分界。中性上傳副本尚未就緒，保護 body 與武器契約 |
| 披風 | 已定位主要垂布；肩背固定環與完整接縫仍未接受。排除整個 131 作披風遮罩的做法 |
| 裙甲／衣料 | 側面鱗甲板與正面多層柔性繡布並存，必須分開處理，不能全部軟布化 |
| 長髮 | 四向可見長馬尾、分束尖端及髮扣；現有 rig 無髮束活動骨。髮根／髮扣固定，新增鏈須先核對 target 相容性 |
| 飄帶 | 正面綠色細條與裙片重疊，獨立飄帶身分／繫點未確認；不得將所有綠色細條歸入飄帶。現有 rig 無飄帶鏈 |
| 手臂／靴部 | 袖布、護臂及靴子在裁切範圍內與披風重疊；保護身體區，不能由白色或既有骨群 seed 判披風 |
| 外側刃狀幾何 | 全身及靴部圖可見腿外游離刃狀件，用途未核對；保留，不擅刪或改武器介面 |

全身一輪視覺覆蓋已執行，但不代表逐面分區或固定配重接受。**S2 仍 PARTIAL，完整語義遮罩 NOT_ACCEPTED。** 原始 authored master 尚未找回；本輪唯讀核對 changshan-longdan 本地 origin/main 與遠端同為 `e85840fad45b7704fab994945aee229f886c3b22`，該樹沒有 `.blend` 路徑，不能聲稱從當前 main 恢復 master。

## 驗證、證據與交付

本輪在起點 SHA 執行 `python -B -m unittest discover -s tests -v`：**379 tests PASS、0 skipped，9.679 秒**；`python -B scripts/pipeline.py validate` PASS（39 assets／11 operations）。兩個案例 driver 語法與 36 圖 hash 回讀 PASS。重複輸出負面測試均以 FileExistsError、exit 1 拒絕，封存影像仍匹配；不是產品失敗或第二次模型候選。

以下路徑相對於既有本地美術隔離工作樹。公開 PR 僅含本文件，不上傳模型、影像或完整幾何資料。

| 證據 | SHA-256 |
|---|---|
| `runs/qa/zhaoyun-s2-root-parts-v001/report.json` | `29cb6e860e50102885476af8766ab887f0c554485d19c450d51b64e392ff95dc` |
| `runs/qa/zhaoyun-s2-body-regions-v001/report.json` | `a5982bde31567c3f87b285d08592a0791b8fc8723b5cb19dafa2fe850f24f47f` |
| 同目錄 `semantic-review.json` | `ccd4012c764a639c1efdc45770b2f84610ff658ca7f101526aee46ac833c1de2` |
| `deliveries/cl-zhaoyun-secondary-v001/v008/manifest.json` | `00d3fd96ccaeea88f250db589bacde844cc5ef93f0f4830cfdc92d73ae8f854f` |

新 delivery ID `cl-zhaoyun-secondary-local-v008` 保留 v007 每個檔案原始 bytes，新增本輪腳本、36 圖、兩份報告、審查表及正／負面與完整測試證據；**134 檔、84,410,284 bytes，逐檔 SHA 回讀 PASS**。`package_complete=false`，保留來源 baseline 與 repo 相依，不能當獨立 Unity 成品。診斷 driver 為 `runs/evidence/zhaoyun-s2-root-parts-v001.py`、`zhaoyun-s2-body-regions-v001.py`；既有核心未另建替代 pipeline。

整體仍 **D0–D5 1/6、NOT_COMPLETED**：D0 PASS；D1 FAIL_NOT_COMPLETED；D2／D4 NOT_COMPLETED；D3／D5 NOT_RUN。兩個歷史修復候選 FAIL、剩餘 0；沒有新模型候選、Mixamo 實際整合、付費或 Unity runtime 修改。下一步為面片層級固定區與接縫語義標註，非直接重配；S3 新修復須具體範圍及新額度，S4 外傳須逐次核准。只有同一接受候選完成全部必要 Unity 遊戲驗收，才可標 SPEC COMPLETE。回滾是不採用診斷集合，原始資產及歷史證據保持可回查。
