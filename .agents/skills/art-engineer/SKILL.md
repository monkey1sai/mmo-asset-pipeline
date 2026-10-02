---
name: art-engineer
description: "製作或修訂本 repo 的 3D 美術資產：將人物、道具、建築、場景需求整理成規格，查素材庫，選擇重用、修改、生成或拆件，完成必要後製、驗收與 Git／LFS 交付歸檔。用於資產委託、現有候選修訂及 Hyper3D 月訂需求規劃；一般玩法程式修改不使用此 skill。"
---

# 美術工程師

以符合需求且可追溯的資產為成果。依委託進度從適當階段接續，完成當次範圍內可執行的工作；不把每件模型強制套用全部製作步驟。

## 工作區與資料來源

此 skill 與 repo 一起保存，從 skill 目錄往上三層取得 repo 根目錄；以下命令從該根目錄執行，不寫死 `C:\Repos`。先讀 [AGENTS.md](../../../AGENTS.md)、檢查 Git 狀態，保留既有變更。核心規格以 [美術工作流](../../../docs/art-workflow.md) 與目前 `scripts/workbench.py` 為準；命令及 schema 改動時先核對實作。

只讀當次需要的資料：

| 情境 | 讀取來源 |
| --- | --- |
| 新需求／修訂 | `requests/`、`library/index.json`、相關資產與 QA；有指定客戶才讀 `projects/<id>.json` |
| 批量需求／月訂 | `catalog/assets.json`、`catalog/monthly-policy.json`、相關 `runs/*.json`，及 [產製流程](../../../docs/production-runbook.md) |
| 實際製作工具 | [能力登記](../../../tools/capabilities.json)，再核對當下可用工具與版本 |
| 驗收／交付 | [證據模板](../../../templates/acceptance-evidence.json)、[交付包規範](../../../deliveries/README.md)、[資產保存](../../../docs/asset-storage.md) |
| 指定遊戲或 Unity 接入 | 選用客戶來源，以及 [首批遊戲／Unity 契約](../../../docs/art-and-unity-contract.md) 的適用部分 |

EvoLoot 與 changshan-longdan 是選用客戶，不能限制核心只能服務這兩款遊戲。其他 repo 預設唯讀；沒有指定引擎時採獨立資產交付。

## 整理需求與設計

保留委託原文，查已有需求 ID 與版本，避免覆寫。新需求可先取得草稿：

```powershell
python -B scripts/workbench.py intake --id wood-gate --brief "木製城門，兩扇門可開關，獨立交付" --type interactive_prop
```

有客戶設定時加 `--profile <id>`。`intake` 只輸出 JSON，協調者以檔案工具保存到 `requests/<id>.json`；它不自動理解尺寸或製作模型。命令中的城門是操作示例，不代表已授權生成。

整理 `purpose`、風格／參考、必須與禁止元素、尺寸／軸向／pivot、面數與貼圖預算、部件與功能、必要骨架／動作、輸出格式、交付範圍及來源。把設計決定和低風險預設寫入 `assumptions`，真正影響製作或交付且無法推定的缺項寫入 `open_questions`；只詢問這些缺項，同時完成不依賴回答的準備。

`size_m` 按 `[X,Y,Z]` 記錄，註明整件／單部件及閉合／展開狀態。面數寫清楚目標、上限或精確值、整件合計／各部件與 LOD 範圍；`texture_px` 是單邊像素尺寸，說明適用貼圖及預算方式，不把建議數值當已量測結果。

依實際用途選任務類型：

| `task_type` | 適用用途與必要檢查 |
| --- | --- |
| `static_prop` | 靜態道具、獨立建築或靜態展示人物；不因名稱是人物就強制骨架 |
| `interactive_prop` | 可開箱、可開門等，先指定分件、pivot、活動方式及範圍 |
| `modular_environment` | 拼接場景／建築套件，指定接合邊、模組尺度與重用要求 |
| `rigged_character` | 要求綁骨的角色／生物，指定骨架、權重、掛點、變形及必要動作 |

非基本需求的 LOD、特殊掛點或其他驗收列入 `additional_checks`。`standalone` 不填目標環境；`target_environment` 才記名稱、版本及實測情境。補齊後改 `status: specified`，執行 `validate`／`plan`，查看 `pending`；缺項不得因結構有效而消失。

活動部件的有符號角度可參考 [城門範例](../../../requests/examples/openable-gate.json)，按實際朝向制定。驗收要涵蓋指定活動全範圍；多部件另檢查獨立與同時活動、需求指定的掛點和穿插，不能只測端點便宣稱全範圍通過。

## 查素材並選製作路徑

```powershell
python -B scripts/workbench.py search "火盆"
python -B scripts/workbench.py validate requests/wood-gate.json
python -B scripts/workbench.py plan requests/wood-gate.json
```

搜尋是文字比對；再查看候選實際外觀、來源、檔案、QA 及未解問題。`needs_revision` 只能作修訂候選，不能直接當交付成品。以需求差距及修訂成本選擇 `production.route`，記錄理由、重用候選和修訂上限：

- `review_existing`：資料不足，先完成比對再決定。
- `reuse`：符合需求，核對版本與交付範圍，不新增生成。
- `modify`：差距可修，保留 master，在新衍生版本修正。
- `generate`：確實缺少且造型需要重做，先整理原創設計參考與生成輸入。
- `split_then_generate`：先設計獨立部件與組裝契約，分別製作；可動門扇／武器／配件不要融合成不能操作的單網格。

剩餘點數不能替代需求。修訂上限目前是規劃欄位，由協調者比對 runs 追蹤，不宣稱程式已強制執行。

## 製作與後製

`plan` 列出能力需求，不執行工具也不授權花費。選目前可用的 Hyper3D、Blender 或其他合適工具；實際模型編輯時才讀適用的建模／拆件／骨架／匯出 skill，不預載整個美術技能庫。能力登記為 `unverified` 時先做範圍內的能力核對，未執行就保持未驗，不能承諾自動骨架、LOD 或 Unity 匯入。

新製作也可採已核實可用的本機新建／程序建模工具，記錄工具選擇與理由。目前 `generate` 計畫列出 `candidate_generation`，能力登記只有 Hyper3D 對應該項，未證明本機新建能力；這個登記缺口不能迫使委託付費，也不能當成 Blender 已可用的證據。

用版本分開 `assets/raw/<asset-id>/<version>/` 與 `assets/processed/<asset-id>/<version>/`，保留唯一 master、來源、工具／參數、操作 ID、大小和 SHA-256。依需求做清理、尺寸／pivot、分件、材質、骨架／權重、指定動畫或 LOD；例如可點燃火盆將盆體與火焰效果分開。外觀不得自行改遊戲規則或碰撞。

需要付費生成時，沿用已存在的具體使用者授權，不重複詢問；缺少必要範圍才請使用者補充。先依產製流程核對即時月訂／普通分項、成本與重置週期，保存 Authorization Envelope 及唯一 `prepared` operation，再送出。舊餘額不是即時證據。未知提交、缺少／未知狀態先查原 operation，不自動重送；失敗／取消先查成本與新證據再規劃修訂。只用授權月訂，不以 skill 或月訂政策擴張為加購、普通點數或排程授權。

工具受阻時先分類，保留需求、版本、輸入與續作條件，完成其餘可執行工作；不以新生成代替失敗的下載或驗收。

## 驗收與交付

分開執行美術、技術、交付完整性與需求指定的環境檢查。參考 `plan.required_checks` 逐項記錄 `pass`／`fail`／`not_run`、實際方法、證據路徑及 SHA-256；證據綁定當前 `request_sha256`，需求或檔案變更後重新核對。

```powershell
python -B scripts/pipeline.py inspect assets/processed/wood-gate/v001/gate.glb
python -B scripts/workbench.py assess requests/wood-gate.json --evidence runs/qa/wood-gate-v001-evidence.json
```

以上路徑需先有實際產物，不能用示例或假檔宣稱驗收。`inspect` 只有局部 GLB 結構清點；`assess` 只核對申報證據與檔案完整性。CLI 退出 0 只表示命令完成，查看 `decision`／`blockers`；`eligible_for_delivery_review` 仍需實際交付審查，不自動變 `delivered` 或 `game_ready`。未驗項目不能填 pass，技術核對不能取代美術外觀或目標引擎實測。

按交付包規範保存 `deliveries/<request-id>/<version>/` 的模型、相依材料／貼圖、預覽、README 與 manifest。記錄規格雜湊、來源版本、各檔大小／SHA-256、驗收紀錄與已知限制；檢查 glTF BIN／貼圖或 OBJ MTL 的包內相對引用，工具不會自動解析完整依賴圖。實際審查通過後才更新素材庫的版本、驗收範圍及 `delivered`；指定遊戲的 `game_ready` 另外驗證。

原始、後製與交付檔皆跟 repo。依 `.gitattributes` 保存大型模型／貼圖，索引與說明用一般 Git。於既有授權範圍只 `git add -- <明確檔案>`，核對工作區 SHA／大小、index LFS 指標和本機 LFS 物件一致；不要盲目 `git add .`。本機納管、commit、遠端 Git／LFS 同步、重新 clone 還原是各自的證據，外部寫入須有對應授權。

交付報告連結需求、模型／預覽、manifest 及驗收證據，說清楚完成範圍、缺口、實際扣點與保存狀態。若未交付，明列目前候選及續作條件；背景工作只有真的在執行時才回報為進行中。
