# 3D 美術工程工作台

這個 repo 管理「理解一份需求，製作並交付符合需求的 3D 資產」的工作流。人物、道具、場景、建築可來自不同客戶或遊戲；EvoLoot 與 changshan-longdan 是首批需求來源，客戶設定可選用，核心不固定綁定兩個 repo 或 Unity。

需求決定是否重用、修改、生成、拆件，以及必要的骨架、動畫、LOD 和目標環境驗收。Hyper3D 與 Blender 等是製作工具。工程師的原始 master、後製版本及交付包保存在本 repo；模型與大型貼圖透過 Git LFS 跟著 repo 走。

## 已實作的離線能力

- 保存自然語言原文為需求草稿，整理規格、來源、預設、待確認項目與交付範圍。
- 搜尋素材庫，制定重用／修改／生成／拆件計畫；依資產類型產生必要驗收項目。
- 核對證據是否對應目前需求及檔案雜湊，列出未驗或失敗項目；輸出待交付審查結果。
- 固定品質標竿與評估條件，從基準開始比較有界修訂；不允許其他高分抵銷任一維度退步，交付核對已評估版本及全部品質目標。
- 保留既有 39 筆模型候選需求、月訂規劃、操作紀錄與局部 GLB 結構清點。

這些工具不連網、不呼叫生成或 Blender、不花點數。`intake` 不會自動解讀出完整尺寸與功能；`assess` 檢查申報證據的完整性，不代替外觀判斷、幾何實測或引擎實測。

## 使用

在此 repo 可使用 `$art-engineer` 處理美術需求。Skill 保存於 [.agents/skills/art-engineer/SKILL.md](.agents/skills/art-engineer/SKILL.md)，會沿現有需求、素材庫、製作、驗收與交付流程操作；客戶與引擎可選用，不自行擴張扣點或外部操作範圍。

例如：`$art-engineer 製作一座可開合的古代木城門，先交付獨立模型；門框與左右門扇分離，資產保存於本 repo。`

使用 Python 3.12 以上，僅需標準函式庫。完整流程見 [美術工作流](docs/art-workflow.md)，資產保存見 [Git／LFS 保存規範](docs/asset-storage.md)。

換電腦時先備妥 Git、Git LFS 與 Python，clone 本 repo 後在根目錄執行 `git lfs pull`，取得大型資產的實際內容；只有 LFS 指標時，模型還不能使用。Repo 內的 `.agents/skills/art-engineer/`、需求、素材庫、工具與資產一起搬移，不需把 skill 複製到全域個人目錄。啟用支援 repo skills 的代理後使用 `$art-engineer`；新機的製作工具、憑證及客戶來源位置仍需各自核對。

```powershell
python -B scripts/workbench.py intake --id wood-gate --brief "木製城門，兩扇門可開關" --type interactive_prop --quality
python -B scripts/workbench.py search "火盆"
python -B scripts/workbench.py validate requests/examples/standalone-stone.json
python -B scripts/workbench.py plan requests/examples/openable-gate.json
python -B scripts/pipeline.py validate
python -B scripts/pipeline.py brief cl-brazier
python -B scripts/pipeline.py inspect assets/raw/cl-brazier/v001/base_basic_pbr.glb
python -B -m unittest discover -s tests -v
```

`intake` 只輸出 JSON 草稿，由協調者保存及補齊。`--profile evoloot` 等參數選用客戶設定；增加客戶只需建立規格檔，不修改核心專案枚舉。`requests/examples/` 是流程範例，不是待扣點工作。

## 檔案位置

美術工程師的新製作／品質修訂採 [品質實驗流程](docs/art-quality-loop.md)，將 autoresearch 的固定評估、baseline、假設、比較與保留紀錄導入模型製作。以 [品質契約](templates/quality-contract.json) 補入需求 `quality`，保存 [實驗紀錄](templates/quality-ledger.json)，再用 `workbench.py compare <request> --ledger <ledger>` 重算結果。工具核對申報證據與規則，不渲染、不評分、不修改模型；美術品質仍須看實際資產。既有未帶 `quality` 的需求保持相容。

| 位置 | 用途 |
| --- | --- |
| `requests/` | 需求、用途、設計約束、製作路徑與交付承諾 |
| `projects/` | 選用客戶風格與限制，首批包含兩款遊戲 |
| `tools/capabilities.json` | 工具能力與已驗／未驗狀態，屬描述資料 |
| `library/index.json` | 工程師資產、版本、來源、驗收與重用缺口 |
| `catalog/` | 既有候選清單及月訂政策，保留首批歷史紀錄 |
| `assets/raw/<id>/<version>/` | 原始模型與貼圖，不覆寫唯一 master |
| `assets/processed/<id>/<version>/` | 清理、拆件、重拓撲、骨架等衍生產物 |
| `deliveries/<request-id>/<version>/` | 獨立交付包、依賴、manifest、預覽及使用說明 |
| `runs/` | 提交、扣點、下載、QA 與視覺證據 |

`assets/unity/` 可保留指定 Unity 任務的衍生版本，核心沒有強制 Unity 步驟。來源理解與選用客戶契約見 [repo 調查](docs/repo-understanding.md) 及 [首批遊戲／Unity 契約](docs/art-and-unity-contract.md)。

既有 `tools/pipeline.py`、`configs/`、`examples/`、vendor 及 [舊 Unity 工作流](docs/workflow.md) 保留為指定 Unity 任務的專用路徑；`tests/test_legacy_pipeline.py` 保留其原測試。一般需求以本文件、`scripts/workbench.py` 與 `$art-engineer` 為入口，不自動套用舊流程的 Unity／FBX 門檻。

## 現有資產與實際完成界線

2026-10-02 首批已生成並下載兩個候選，月訂實際使用 1 點。當時完成後網頁月訂 204、普通 25、API 合計 229；這是歷史快照，每次新的付費操作都需重新核對分項與帳單週期。

| 候選 | PBR 三角形清點 | 美術狀態 | QA |
| --- | --- | --- | --- |
| 常山龍膽火盆 | 2,500 | needs_revision：靜態火焰、金屬支腳偏離需求 | `runs/qa/cl-brazier-v001.md` |
| EvoLoot 普通鐵劍 | 1,800 | needs_revision：雙叉刃及金色裝飾偏離鏽鐵劍 | `runs/qa/evoloot-iron-sword-neutral-v001.md` |

兩件的 Hyper3D 來源頁保持私有；四份 GLB 與一張貼圖實際保存於 `assets/raw/`，索引、原始操作紀錄及 QA 一起納管。來源頁可見性與 Git repo 可見性分開：目前 GitHub 遠端為公開，本次經使用者授權推送的檔案隨 repo 可讀。它們尚未交付，沒有 Blender 後製、遊戲接入或 Unity 驗收。普通史萊姆只有 `prepared` 草稿，尚未提交、扣點；查同一 operation 及即時餘額後才能續作。

原始 38 筆新增候選的基礎費估算共 19 點，需求量不足以吸收初始 205 點。月訂政策按正在交付的需求、已規劃需求、有明確用途的素材庫資產配置；不固定分配兩個遊戲比例。模型修訂取決於需求差距，不能為耗點重複生成。

Git LFS 設定、本機暫存、Git／LFS 遠端同步及重新 clone 還原各自需要證據；保存進度見 [Git 可攜性紀錄](runs/qa/git-portability-20261002.json)。舊 QA 中的未提交／未推送欄位是當時快照，不代表後續同步狀態。本 repo 不保存憑證或臨時下載網址，不自行加購、升級、修改可見性或建立排程。另兩個遊戲的既有變更保留。目前沒有背景生成或排程繼續執行。

2026-10-02 已實際完成內容提交的 Git／LFS 遠端同步，並從 GitHub 全新 clone，以空白獨立 LFS 儲存區還原五個資產、核對雜湊及執行 62 個離線測試。這驗證 repo 還原，不表示新電腦的 Blender、Unity 或代理 UI 已驗收；兩個候選仍需修訂。

本機曾出現 `sandbox provisioning failed`；個別經核准的原使用者環境檢查不能證明正常沙箱已恢復。驗證紀錄需清楚區分工具測試、模型實測、目標環境與遠端保存證據。
