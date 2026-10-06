# 美術品質實驗工作台驗證

日期：2026-10-02（Asia/Taipei）。範圍：依使用者要求學習 karpathy/autoresearch，將可比較、有界的品質實驗導入本 repo 的美術工程師與離線工具。未受託製作特定新模型；沒有生成、扣點、下載、Blender／引擎實測、commit、push、PR、部署或排程。

## 原始狀態與方法

- 開始時 `main` 工作區乾淨，基底 `c990639962b7ce85eb6beb631057aa4d76a3e86d`。
- 本次在 repo 內 `tmp/art-quality-loop` 的 `codex/art-quality-loop` 分支隔離修改與驗證，再將明列檔案同步回原工作區；沒有提交或更新遠端。建立工作樹的單次命令使用停用 hooks 的路徑設定與 `GIT_LFS_SKIP_SMUDGE=1`，未修改任何全域／永久設定。
- 已讀 [autoresearch README](https://github.com/karpathy/autoresearch/blob/master/README.md)、[program.md](https://github.com/karpathy/autoresearch/blob/master/program.md)、[prepare.py](https://github.com/karpathy/autoresearch/blob/master/prepare.py)。使用方法概念；未執行第三方訓練程式。來源 master 可變，日期表示閱讀時間。
- 導入固定需求／標竿、baseline、每輪假設、同條件比較、逐維度不退步、最佳版本與失敗紀錄、次數／時間預算及交付內容綁定。
- 視覺平手且修復原必要門檻為 `keep_for_gate_repair`，只稱門檻修復，不稱美術提升。

## VERIFIED：本次執行證據

| 檢查 | 結果 | 能證明的範圍 |
| --- | --- | --- |
| 修改前 `python -B -m unittest discover -s tests -v` | 62 tests passed | 原工具基準；不含模型美術 |
| 修改後同一離線測試命令 | 84 tests passed | 既有 62 項加 22 項品質契約／比較／交付測試；合成檔案及申報 |
| `python -B scripts/pipeline.py validate` | valid，39 筆（17 evoloot、3 shared、19 changshan-longdan） | 既有清單結構，未驗來源新鮮度或 runtime |
| system skill-creator `quick_validate.py .agents/skills/art-engineer` | `Skill is valid!` | 技能 frontmatter／格式，UTF-8 模式；不代表美術能力實測 |
| `intake --id quality-smoke --brief ... --quality` | 輸出有效品質 draft | 新 CLI 參數可用，不自動推論完整規格、不製作模型 |
| 上述草稿 `plan` | 包含固定契約 hash、次數／時間上限與保留規則 | 離線計畫，仍有需求及品質 pending |
| 上述草稿搭配未填 `templates/quality-ledger.json` 執行 `compare` | `quality_target_met: false`，`next_action: stop_blocked` | 缺失 baseline、參考／契約不符及未填規格不會被當成 PASS |
| `git diff --check` | 通過 | 差異空白格式；不代表 runtime |

新增測試涵蓋：高總分掩蓋單項退步、對最佳而非最後淘汰版本比較、各項目標、飽和平手、已知失敗後修訂、必要門檻修復、未知操作停止、次數／單輪／總時間、缺少視角／分數／subject、需求／契約／參考／檔案變更、草稿品質契約、缺失或改動交付貼圖、交付內容不同、相同內容換包內路徑、缺失 hash 與舊需求相容。

## 獨立審查

依當次 Shared Agent Core 的交付前要求安排唯讀 reviewer。Jev 回傳確定性 `architecture_review`，`provider_called: false`，沒有外部 API 執行。分派要求為 `gpt-6-astra`／`high`；工具未提供可獨立核實的實際模型／effort 欄位，不將所選設定寫成已驗 runtime 身分，也不是人類批准。

第一輪以獨立合成 probe 找到兩項 P2：

1. completed 候選的已知技術 fail 被當成不可恢復證據錯誤，使後續修訂全部 blocked。
2. 允許技術 fail 的滿分 baseline，但視覺平手的技術修復永遠被 discard。

已分離 `failed_gates` 與無效 `issues`：合法已知門檻 fail 是 discard；未知操作、無效證據與預算仍停止。另加入 `keep_for_gate_repair`，仍禁止任一視覺維度退步。

第二輪唯讀複核獨立執行兩項聚焦回歸測試，2 tests passed，並以原序列確認已知失敗保留且計入 2 次候選／180 秒，新合格候選可保留，先前已達標版本也不會因後續已知失敗失去交付審查資格。Reviewer 確認兩項 P2 關閉，修正範圍無新增阻擋交付問題。

## 環境與限制

正常沙箱命令起始失敗：`sandbox provisioning failed`，分類 `ENVIRONMENT_FAILURE`。本次讀取與離線驗證透過逐命令 `require_escalated` 自動審查完成；這不證明正常沙箱恢復。未變更 ACL、safe.directory、全域設定、hooks 或安全控制。

工具只核對申報與本機檔案一致性，沒有執行美術評分、固定視角渲染、DCC／引擎、完整相依引用解析、append-only 儲存或執行時預算終止。文件／分數／雜湊都不能證明模型已達「頂尖」。新 skill 要求新品質任務補品質契約，舊 CLI 需求仍可不帶 quality；這是相容設計，不是所有歷史模型已重新驗收。

本次沒有真實資產 baseline／after 比較，也未改動素材庫既有兩件 `needs_revision` 狀態。下一件實際委託應固定標竿與用途，使用此流程產出多視角及實測證據，才能判斷實際品質提升。

目前沒有背景生成、審查或排程繼續執行。當次授權的流程整合無待決定事項。

同步回原工作區後再次驗證：Python 3.12.7，84 tests passed（0.949 秒）、39 筆清單 valid、skill validator 通過、`intake --quality` 輸出 draft、`git diff --check` 通過；10 份同步檔案 SHA-256 與審查工作樹一致。這是原 repo 的本次驗證，不引用其他 repo 歷史結果。
