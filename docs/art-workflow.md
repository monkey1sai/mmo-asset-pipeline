# 需求驅動的美術工程工作流

本 repo 是美術工程師的工作台：以交付需求為中心管理設計、製作、驗收與可重用資產。客戶和製作工具可替換，完成條件由需求決定。首批兩款遊戲保留在選用客戶規格與歷史清單，不構成核心的專案限制。

```mermaid
flowchart LR
  A[自然語言需求] --> B[規格與設計參考]
  B --> C[查素材庫與需求差距]
  C --> D[重用／修改／生成／拆件]
  D --> E[必要後製]
  E --> F[美術與技術驗收]
  F --> G[需求指定的環境實測]
  F --> H[獨立資產交付]
  G --> H
  H --> I[repo 交付包與素材庫]
```

環境實測只有指定 `target_environment` 時才需要；圖中的兩條交付路徑由需求決定。任何檢查失敗或未做都要留下缺口，不能跳成通過。

## 需求與預設

`scripts/workbench.py intake` 接收原文、ID、任務類型及選用 profile，只輸出草稿，不默默寫檔、不自動推斷完整規格。協調者保存到 `requests/<id>.json`，讀取原文與參考後整理：

| 欄位 | 用途 |
| --- | --- |
| `brief`／`purpose`／`provenance` | 原始需求、使用場景與來源；可來自人類委託，不必有遊戲 Git HEAD |
| `task_type`／選用 `project` | 資產行為與客戶設定，project 可省略／null／新增 slug |
| `style` | 風格、參考、必須／禁止元素 |
| `spec` | 尺寸、公尺／軸向、面數、貼圖、部件 pivot／動作、骨架與動畫 |
| `production` | 路徑、理由、重用候選及修訂上限 |
| `delivery` | 指定格式、standalone 或明確環境的版本與實測情境 |
| `additional_checks` | 需求指定 LOD、穿插、掛點等額外檢查，不能覆寫基本檢查 |
| `assumptions`／`open_questions` | 可修訂預設與真正需要補齊的缺項 |

`status: draft` 可合法記錄未知尺寸／面數；`validate` 只檢查結構，`plan` 的 pending 仍會指出缺項。補齊後改為 `specified`，不表示已核准付費或驗收通過。無貼圖需求可用 `texture_px: null`；有貼圖則用正整數，非固定只有 1K／2K。

可先採公尺、+Y 上、+Z 前、GLB 獨立交付，明確記成可改預設。影響玩法、可動結構、角色骨架、精確接合或最終交付的缺項需先解決。範例文件只是示範；不以它們發起生成。

## 製作選擇與工具

先搜 `library/index.json` 並查看實際檔案、版本、QA 和未解問題。搜尋是文字 metadata 比對，不是自動形狀相似度。相符就重用；小差距修改衍生版本；主要輪廓不符才重估生成；可互動或組合資產先拆件。修訂上限是規劃欄位，目前不會自動計算已用次數或強制執行。

`tools/capabilities.json` 是能力登記，不是插件執行器或授權。核心計畫描述「候選生成、模型編輯、格式輸出」，協調者才選目前可用工具。Hyper3D 操作及月訂範圍依 [製作流程](production-runbook.md)；Blender 等未驗能力保持未驗，不宣稱一鍵產製。

`catalog/assets.json` 保留首批批量候選。原 repo source 的 path／line／head 仍須完整；新清單可用 brief／reference／library 類型來源。專案 ID 不再限制兩款遊戲；`pipeline plan --project standalone` 可篩選 project null。未知、缺少操作狀態會停止規劃，失敗／取消也不自動釋出成可重送。

`generate`／`split_then_generate` 的 `plan` 另提供 `creation_workflow`：由美術工程師整理每件／部件輸入，優先透過已核實的 Hyper3D API 創作，並追蹤、下載和後製。API 可用性、圖生輸入、額度來源與付費授權分開核對。網站是額度查核或有理由的備援；完整步驟見 [API 創作流程](api-creation-workflow.md)。離線計畫不直接提交生成。

## 按用途驗收

| 類型 | 基本美術／技術／交付之外的檢查 |
| --- | --- |
| `static_prop` | 沒有強制角色骨架或引擎門檻 |
| `interactive_prop` | 至少兩部件、pivot、活動方式／範圍、活動測試 |
| `modular_environment` | 接合邊與重用規格實測 |
| `rigged_character` | 骨架／權重／掛點及關節變形，需求列動畫時再檢查動畫 |

每件都有造型符合度、尺寸／pivot、幾何／指定材質、交付完整性。LOD 及其他要求明確放入 additional_checks；`target_environment` 需 name、version、verification_context 及該環境證據。

`plan` 回傳 `request_sha256`，以排序鍵、UTF-8、無多餘空白的 JSON 計算規格雜湊；需求改變後舊證據不再相符。證據格式參考 `templates/acceptance-evidence.json`：填入實際 request ID／雜湊；每項 `pass` 必須記方法及至少一份存在的檔案／SHA-256；未做是 `not_run`，失敗是 `fail`。輸出格式必須有相符交付檔。

```powershell
python -B scripts/workbench.py plan requests/examples/standalone-stone.json
python -B scripts/workbench.py assess requests/examples/standalone-stone.json --evidence templates/acceptance-evidence.json
```

未填模板必然得到 `not_ready`，此命令不是產出真實驗收證據。CLI 退出 0 表示核對正常執行，應查看 decision／blockers，不能把退出碼當素材 PASS。合格申報得到 `eligible_for_delivery_review`：只是進入交付審查，沒有自動 `delivered`／`game_ready`。

證據內容仍由實際檢查者負責；SHA-256 只能證明內容一致，不能證明造型正確、物理尺寸或效能。工具只讀 repo 內的 assets、deliveries、runs/qa、runs/evidence 檔案，拒絕跳出 repo 及設定／憑證區。它不自動解析 glTF／OBJ 依賴圖；依賴需在交付列表登記並實際驗證引用。

## 交付與工程師資產

按 `deliveries/README.md` 保存交付包與 manifest，實際審查後才在素材庫登記 `delivered` 及完成範圍。獨立資產可以完成交付，同時保持目標環境 `not_requested`；如後續要求 Unity，另開目標版本任務並驗證。

master、衍生版本和交付包均隨 repo，透過 Git／LFS 保存；保留用途、來源、工具／參數、版本、檔案／雜湊、預覽、已驗／未驗及重用條件。不得只保存 Hyper3D 雲端網址。詳見 [資產保存規範](asset-storage.md)。

本次工具不會自動下載、修改模型、複製交付檔、更新索引或執行 Git；這些由協調者在已授權範圍內完成。目前素材庫兩件仍 `needs_revision`，沒有新的已交付資產。
