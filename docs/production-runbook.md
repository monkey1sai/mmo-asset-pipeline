# 製作與月訂資源流程

核心依 [美術工作流](art-workflow.md) 及需求單執行：先確定用途、設計與交付範圍，查素材庫，再選重用、修改、生成或拆件。客戶 repo 預設唯讀；沒有指定目標環境時，交付獨立資產。離線 CLI 不扣點、不執行 Blender，也沒有無人值守生成或月排程。

需求整理後的 API 創作入口依 [美術工程師 API 流程](api-creation-workflow.md)。預設由工程師操作可用 API；以下網頁分項查核是額度證據，不是要求改用網站生成。API 認證、月訂額度來源及本次花費授權分開保存。

## 製作前

1. 閱讀 AGENTS、需求與適用客戶規格。核對來源版本、已有 master、需求差距與剩餘修訂預算；重用不提交生成。必要部件、pivot、活動範圍、骨架／動作／LOD 由需求決定。
2. 用 `workbench.py validate` 與 `plan` 列出缺項、製作路徑及驗收項目。範例、客戶設定、有效 JSON 或離線計畫不是付費授權。
3. 需要 Hyper3D 時，使用受支援的憑證提供者查 API 總餘額，在已登入官方網頁確認月訂／普通／凍結分項。API 總數不能替代月訂證據；不讀取、列印或保存 key、cookies、signed URL。
4. 確認實際帳單重置時間、單次費用與本次授權上限。2026-10-02 曾觀察最後補入為 2026-10-01，下一次重置未核實；不可由曆月推定日期。首批曾採 4 點上限，僅是該批保護限制，不是新批次授權。
5. 付費前在 runs 保存唯一 operation ID、request ID／規格雜湊、工具、prompt／參數、成本、輸出目錄及 Authorization Envelope，狀態 `prepared`。先保留記錄再送出，每次只開一筆。

Authorization Envelope 記 Destination、Purpose、Allowed operations、Data、Forbidden operations、Stop conditions。原創 prompt／參考圖是傳送資料；保守預設僅使用已授權月訂，不動普通點數，不加購、升級、公開發布、寫其他 repo、push、部署或建立排程。資料或操作範圍改變時重新界定。

## 生成與狀態

- 已接觸的 `hyper3d.rodin_generate` 可文字生成；首批使用 `Gen-2.5-High`、`Raw`、按資產 `quality_override`、GLB，每件實際扣 0.5 點。這是首批事實，不保證任何後續模型、工具或設定同價。
- 另一整合 `hyper3d_api.rodin_generate` 的固定圖生設定與輸出根目錄限制不同，不能照搬首批低面數需求；製作前核對目前工具能力。能力紀錄見 `tools/capabilities.json`，未經驗證的能力不能當成可用。
- 回傳後立即保存 generation ID，改為 `submitted`，查同一 ID。`pending`／`queued`／`processing` 是等待；服務 `completed` 才記 `generated`。
- 提交逾時或結果不明記 `unknown`，先查同一 ID／帳戶 Mine，不自動重送。未知或缺少狀態使離線計畫停止；失敗／取消仍保留舊操作，先分類、查成本與新證據，再規劃新修訂。
- 完成時只保留永久展示頁等非秘密來源。臨時 `files[].url` 僅供授權下載，不進 repo、log 或回覆。每筆實際扣點及下載結果分開登記。

## 下載、製作及保存

優先使用可返回本機路徑和雜湊的下載工具。若出現 `PATH_OUTSIDE_AUTHORIZED_ROOTS`，不改全域授權設定；可用已登入的官方瀏覽器下載。等待逾時先核對下載是否已完成，不因下載問題重新生成。

ZIP 解壓前核對項目、大小、解析後目的地仍在 repo、無路徑跳脫，且不覆寫既有版本。原檔存 `assets/raw/<id>/<version>/`，衍生存 `assets/processed/`。保留 master、必要來源包及每檔 SHA-256；依 [資產保存規範](asset-storage.md) 用 Git／LFS 納管。

```powershell
python -B scripts/workbench.py search "火盆"
python -B scripts/workbench.py plan requests/examples/openable-gate.json
python -B scripts/pipeline.py validate
python -B scripts/pipeline.py inspect assets/raw/cl-brazier/v001/base_basic_pbr.glb
python -B -m unittest discover -s tests -v
```

`inspect` 只清點 GLB 容器、基本 buffer 範圍與報告列出的結構，不是完整 glTF 驗證，不驗 UV／法線品質、實際尺寸、pivot、權重、動畫、LOD 或引擎呈現。美術與技術證據分開保存。造型偏離需求標 `needs_revision`，不要因下載成功而標成已交付。

後製依需求執行：普通石頭無需綁骨；可開城門需分件及鉸鏈測試；角色需指定骨架／變形；火盆如需可點燃，盆體與動態火焰分開。此 repo 尚未驗證 Blender 執行、通用骨架／LOD 自動產製或 Unity importer。

官方可見性標籤是下一個動作：`Set asset public` 表示目前私有，`Set asset private` 表示目前公開。核對鎖頭及重新開頁讀回；不由 checkbox pressed 推定。預設不改公開、不點外部發布。

## 驗收、交付及下月續作

逐項執行需求中的美術、技術、交付及必要目標環境檢查，記錄方法、結果、檔案和雜湊。`assess` 只核對證據契約及完整性；必須另外實際判斷素材是否符合需求。獨立資產可按自身規格交付，沒有 Unity 需求就沒有 Unity 門檻。

交付包在 `deliveries/<request-id>/<version>/`，包含模型、相依材料／貼圖、說明、manifest、預覽和驗收紀錄。素材庫索引記錄版本、來源、檔案、已驗／未驗與重用條件。指定遊戲接入時才依客戶契約及真實版本測試，不自行改遊戲規則或碰撞。

每次重新開始都核對即時餘額、重置週期、需求、素材庫與 runs。`pipeline plan` 排除重用及保留操作，但不是外部交易鎖。月額度按進行中交付、已規劃需求、有用途的素材庫資產配置；剩餘額度大於需求時回報缺口，補足設計與後製能力，不無用途重做。

正式排程需另有具體頻率、上限、重置依據及持續扣點授權。目前沒有月排程或背景生成。commit、Git／LFS 同步與全新 clone 還原依當次使用者授權及 `runs/qa/git-portability-20261002.json` 證據判讀；本機 LFS 物件不能當成遠端備份證據。
