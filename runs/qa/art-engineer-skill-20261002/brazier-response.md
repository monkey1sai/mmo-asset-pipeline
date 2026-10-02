# 火盆素材交付問題：離線試用回覆

狀態：已完成本次問題判斷；現有下載檔不能直接算交付完成。沒有製作或交付模型。

原始模擬需求：「幫我從現有素材庫拿火盆交付，但要沒有靜態火焰、石座；現有下載檔能直接算交付完成嗎？只處理這個問題，不生成。」

VERIFIED（本輪讀取的本機資料）：`workbench search 火盆` 找到 `cl-brazier-v001`，素材庫標為 `needs_revision`；美術是 `needs_revision`、技術是 `inventory_only`、交付是 `not_delivered`。素材庫與 QA 均記錄靜態火焰需處理及金屬支腳／石座目標不符。已檢視 QA 引用的本機截圖，可看到火盆內火焰外觀與金屬支腳；截圖是先前產製證據，不是本輪線上實測。原始 GLB 的本輪結構或火焰拓樸未檢查。

INFERRED（判斷與處理方向）：無靜態火焰的條件已與現有 QA 記錄衝突，因此應保留 v001 為候選，不能改為 delivered。若之後另開後製任務，要在新衍生版本處理火焰幾何並檢查底座；只關閉 emissive 不能證明火焰幾何已移除。「沒有靜態火焰、石座」的石座語義可能是「無火焰且要石座」或「火焰與石座都不要」，需在後製委託前寫清楚；這不影響目前不能直接交付的判斷。

做到交付完成仍需與明確需求綁定的美術、尺寸／pivot、幾何／材質、交付完整性證據，保存 GLB、必要相依材料／貼圖、預覽、README、manifest 與驗收索引。`assess` 即使回傳 `eligible_for_delivery_review` 也只代表證據契約可進入交付審查；實際審查通過後才可更新 delivered。獨立交付沒有指定 Unity 或遊戲，不強加該環境驗收。

依據：

- `.agents/skills/art-engineer/SKILL.md` 的「查素材並選製作路徑」及「驗收與交付」。
- `library/index.json` 的 `cl-brazier-v001`、acceptance、open_issues。
- `runs/qa/cl-brazier-v001.md` 的 VERIFIED、INFERRED、尚未驗證。
- `runs/qa/cl-brazier-v001-inventory.json` 的 `structural_inventory_only` 與 `not_verified`。
- `runs/evidence/20261002-cl-brazier-private.jpg`：本輪實際查看的歷史成品截圖。
- `deliveries/README.md` 與 `docs/asset-storage.md` 的交付包及來源保存要求。

限制與下一步：本次只回答交付狀態與依據；未執行 Blender、付費生成、下載、後製、外觀／技術驗收、交付包寫入或 Git mutation。沒有新花費，沒有背景工作繼續執行。後續若要真的修訂，先把石座條件寫成明確需求，再安排有授權的後製及驗收；此回覆本身不啟動該任務。
