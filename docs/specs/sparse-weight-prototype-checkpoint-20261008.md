# 稀疏配重修訂與第一個局部 prototype checkpoint

整體 spec 仍為 **1/6、NOT_COMPLETED**。新增可重用的局部配重工具；第一個趙雲模型候選實際失敗，未選用。原版 Unity 已建立引擎測試基準，但完整遊戲與修復候選驗收未完成。

## 工具與操作

擴充既有 `scripts/cv1_restore_glb_weights.py` 的 parser／accessor span，而非建立另一套資產或來源流程。`patch_vertices(blob,node_name,changes)` 只改一個 primitive 中指定原始 POSITION ID 的 JOINTS_0／WEIGHTS_0。要求合法、唯一骨名與 ID，1–4 個正配重且總和約1；拒絕 interleaved／normalized／額外權重組、共享 mesh/accessor、重疊 bufferView 與越界。除指定 slot 外所有位元組完全一致，包括 JSON、rest、拓樸、UV、材質、嵌入貼圖、其他頂點及武器。

```powershell
python -B scripts/cv1_restore_glb_weights.py --patch --request requests/REQUEST.json --source-root SOURCE_ROOT --asset MODEL.glb --sha256 SOURCE_SHA256 --profile configs/PATCH.json --out assets/processed/ASSET/NEW_VERSION/MODEL.glb
```

Profile 包含 canonical `request_sha256`、`source_sha256`、`mesh`、`changes` 與 `review`。Changes 每筆為 `{"vertex":1,"weights":{"cloth":1}}`。Review 為 `{"status":"local_prototype_accepted","reviewer":"ACTUAL_REVIEWER","original_vertex_ids":[1],"evidence":{"path":"runs/evidence/REVIEW.md","sha256":"EVIDENCE_SHA256"}}`。ID清單須與changes完全一致，證據須存在且雜湊吻合。這是宣告核對，**不是機器認證人類 approval**。

CLI 沿用 identity、workbench、art_sources 的路徑／no-reparse 與 embedded_glb_only。輸出與報告都拒絕覆寫；禁止外部／data URI。未檢查美術、修訂時鐘或素材公開權利，不放行 Mixamo 原始再散布。協調者仍須先確認本地用途授權、剩餘預算及語義範圍，再跑完整幾何、DCC、動作與目標 runtime。

## D1 計畫與實際候選

獨立需求審查確認原 draft request 的 max_revisions=0 是診斷階段協調者自設的保守值，非模型候選已耗盡證據。新 request v002 保留舊版；採最多2候選、單輪1800秒、基準／製作／驗證共3600秒的保守計畫。這些數字不是使用者回答先前選項；歷史診斷耗時 UNKNOWN 保留，E12量測器上限不變，不宣稱舊7200秒全數剩餘。

新 D1 階段真實起時計為2026-10-08T14:00:31.354786Z。第一個候選起迄14:08:42.225013Z–14:31:14.741176Z，實際1352.516秒，含驗證、工具完整性與審查；累計1843.386秒。完整品質baseline／評分仍未完成，紀錄是局部失敗attempt，不能拿來做整角色quality PASS。

已視覺審查的白色衣料局部清單是 **21** 個 ID（先前22是另一甲片範圍，已在產生模型前更正；ID清單未變）。候選單一假設為此局部改為cape_02=1。新GLB僅改338bytes；共用工具重現同bytes，未製作第二個候選。

候選 SHA-256：`8313b2bd18e151fd8acb5313fb2f369be7a0f1fd87b02494ccd81cfabb5b81d2`。原始 SHA：`7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33`。

| 條件 | 基準 | 候選 | 結果 |
|---|---:|---:|---|
| idle_once異常邊 |3376|3386|FAIL；新增23條，並非只看總數|
| idle_once原邊1352↔1116 |0.477924m|0.006741m|局部邊改善，無法抵銷邊界退步|
| idle_2_seconds異常邊 |3380|3389|FAIL；新增22條|
| Blender右腿30度異常邊 |866|874|FAIL|
| Blender披風30度異常邊 |1636|1662|FAIL|

24個跨遮罩三角形、26條跨界邊及16對近乎重合的未修改頂點全部列入證據。單骨與rest共8組Blender／CPU全頂點對照最大誤差約2.712e-7m；這只確認測量一致，不能將候選FAIL改為PASS。保存FAILED-local-prototype.blend及基準／候選圖片。cape head-tail是製作候選後才記錄，明示此限制，不冒稱前置觀測已完成。

擴大範圍的唯讀診斷找到496頂點／812面的連通片；圖中可見白色衣料及下方裝飾表面，尚未確認完整部位身分。近乎同位置合併會牽入其他片，logical weld接近整件角色。幾何連通不是衣料語義；804頂點提案仍NOT_ACCEPTED，不直接套配重，不消耗第二候選。

## Unity 原版基準

隔離副本固定於遊戲 `805db86f67ab2be152dea8abe57ca47f4e735fb7`，同 SHA 原GLB；Editor6000.6.4f1_12bfff696524。沿用未修改的遊戲unity-validate runner，run `0f83fa5d-dc2f-4b6e-b5d0-09379ae221b6`：compile、164EditMode、47PlayMode（0skipped）、Windows build、可見Player啟閉均PASS。Player實際非batch、focused、1920×1080／Direct3D11；source snapshot與Git保持不變，沒有E12量測器修正。

實際scene仍有大片衣料尖三角與拉伸，**角色視覺FAIL**。這是原版工程baseline，不是修復候選或完整遊戲驗收；natural human play／performance acceptance／全部玩法場景NOT_RUN。Jev只參與既有審查路由，沒有啟動或操控Unity。

Unity result SHA：`4c07c72e3190f9b24d3cbe5edc9f22ce733e21036fc80cb6c8fc629e69f371e3`；scene SHA：`6ab0d24b6991ab657b0ff638b0bded5f1a798e3ad5cce07f73a2842f55354619`。本公開checkpoint不包含模型、貼圖、動畫或完整圖片。

## 驗證與後續

17項新增單元測試涵蓋非目標bytes、no-op、合法配重與拒絕條件、CLI綁定／scope／覆寫／report collision／來源漂移／URI。獨立審查另重現負buffer偏移會寫到BIN前、配重accessor與COLOR共用會同步改色；已拒絕負值／boolean索引與偏移、所有primitive語義／morph／indices／animation／inverseBind引用共用及image／sparse／extension直接bufferView共用，新增回歸檢查。修正後checkpoint全套364項、美術工作區全套369項unittest PASS，pipeline validate均valid；真實CLI新run v002同bytes正面與5項拒絕檢查PASS，沒有覆寫v001。PR15已由monkey1sai於14:20:24Z合併為main84fdbd92，該main的隔離合併後347項測試及validate PASS；這是GitHub merge紀錄，reviews仍空，不偽造UI approval。首次檢查在worktree checkout完成前誤啟動，為環境準備失敗，原log保留，不算產品FAIL或PASS；完成checkout後才取得上述合併後結果。

本次工具完整性可独立使用，失敗候選不能接入或上傳。下一個模型候選需先確認連通片與接縫的真實衣料範圍及固定掛點，不擴大遮罩遮蔽失敗。Mixamo實際綁骨／走跑跳、完整四類次級骨、真實target rig重定向、合法交付及Unity完整修復候選驗收仍未完成。可revert工具commit回滾；原始、失敗与歷史證據保留。
