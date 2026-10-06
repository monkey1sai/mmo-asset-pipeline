# 固定評估的美術品質實驗

目的：把「再生成一次看起來更漂亮」變成可比較的資產修訂，讓每輪對具體需求有貢獻，並保留最佳版本、失敗與交付依據。新品質任務由 `$art-engineer` 使用此流程；舊需求保持相容，不偽造歷史 baseline。

## 來源與轉譯

2026-10-02 閱讀 [karpathy/autoresearch README](https://github.com/karpathy/autoresearch/blob/master/README.md)、[program.md](https://github.com/karpathy/autoresearch/blob/master/program.md) 及 [prepare.py 的固定評估](https://github.com/karpathy/autoresearch/blob/master/prepare.py)。採用方法概念，未引入訓練程式、套件、GPU 訓練或第三方執行指令；master 可變，此日期表示閱讀時間。

| 原始方法 | 美術工程的對應 | 保留理由與界線 |
| --- | --- | --- |
| baseline 先跑一次 | 先保存真實現有候選與全部固定視角、檢查及分數 | 才能知道修訂改善了什麼；無模型就先準備，不能填假 baseline |
| 固定且不可修改的評估 | 凍結需求、參考、0..5 評分錨點、用途尺度與渲染／檢查條件 | 避免換光照、改風格或降低門檻美化結果 |
| 單一受控實驗範圍 | 每輪針對一個可觀察差距提出假設，修改新候選版本 | 比較失敗時容易回到最佳 master；不是限制只能使用一種工具 |
| 固定訓練時間 | 每輪時間、總時間及既有修訂次數上限 | 預先規劃可比較的資源範圍；3D 不照搬五分鐘，實際生成另受付費授權限制 |
| improved → keep；else discard | 所有品質維度不退步，至少一項提升才算美術改進 | 多個維度不能以平均分抵銷缺陷；平手且修復最佳版本原有必要門檻另列技術修復；discard 只是不選用，仍保存產物 |
| 實驗結果紀錄 | 保存每輪假設、來源版本、預覽、檢查、分數理由、耗時及工具狀態 | CLI 重算結論，不信任自行填寫的 keep 標籤 |
| 相等時偏好簡單 | 平手且無必要門檻修復時保留既有最佳；必要簡化另開有可量測成本目標的需求 | 本版不把飽和／平手宣稱美術改善，避免主觀複雜度成為跳過證據的理由 |

本地實驗有停止條件，權限及付費規則沿用 repo。原文的無限迴圈、停用權限、自動 commit/reset 與不保存結果的 Git 做法不適用；本流程保留來源和全部候選，沒有背景排程或自動扣點。

## 建立可評估的品質目標

使用 `intake --quality` 在新需求附上 [品質契約模板](../templates/quality-contract.json)，或將模板複製到既有需求的 `quality` 物件；模板本身不是需求。先按用途補齊原本的尺寸、幾何、功能、來源及交付格式。模板預設 `status: draft`，只能規劃；參考與參數尚未填妥時不能做有效比較。

品質契約包含：

- `protocol`：唯一視角 ID 列表、固定光照、背景／色彩管理、鏡位／尺度、實際工具版本與檢查情境。建議五視角；形變角色加需求指定姿勢，模組加拼接情境，獨立道具不強制骨架或引擎。
- `reference_artifacts`：repo 內有權使用的本機參考或原創設計板，登記 `path`／SHA-256；保留來源與權利說明。網站連結不能替代比對用的實際檔案。
- `dimensions`：每項有唯一 `id`、可觀察 `criterion`、六個不同的 `anchors`（0..5）及 `target`（1..5）。模板涵蓋設計意圖、輪廓、比例、材質、收邊、用途辨識度；按風格與用途修改，不把寫實標準套在風格化模型上。
- `budget`：正整數 `trial_seconds`、`total_seconds`，基準也計時；最多候選輪數沿用 `production.max_revisions`。示例數字是可修訂規劃，不是已授權的生成成本。

追求標竿品質時，各適用維度通常至少到達 4（全部核心要求符合），關鍵維度以具體標竿的 5 為目標。這是設計判斷，不是業界通用數字或模型品質保證。不要為湊分增加無用細節、面數、金色裝飾或不符用途的寫實材質。

把 `quality.status` 改為 `frozen` 後執行 `plan`，記錄 `request_sha256` 和 `quality_loop.protocol_sha256`。後者涵蓋整個品質契約（含標竿、目標、時間）；改契約或需求會使舊紀錄失效。若用途真的改變，保留舊版並建立新需求版本與 baseline；不能降低門檻讓舊版本過關。

## 有界實驗與工藝

先建立一件真實 baseline。所有適用檢查都要做並記錄；baseline 可以有明確失敗，但不能把未做當成失敗後直接打分。尚無能評估的候選、必要工具或參考時保存 draft，報告阻礙。

優先次序由需求差距決定：

1. 先修主要輪廓、比例、結構或用途障礙；例如普通鐵劍的雙叉刃比金屬粗糙度更優先。
2. 活動件先滿足分件／pivot／活動全範圍；角色在必要姿勢檢查變形；模組在接合處比較。不自行變更遊戲碰撞或規則。
3. 再修材質分區、UV／貼圖、表面與收邊；同時查看灰模、線框、背面、底面與近景，禁止只靠一張 beauty render。
4. 新候選按相同條件檢查、評分，逐維度寫出觀察理由，使用 `compare` 決定是否成為下一輪來源。重用／本機修改／重新生成仍依修訂成本選擇。

每輪只有一個主假設，但必要的相依修正可一同記錄；例如刃形更改後的 UV 與法線修復。保存新的 master／export 版本及相依素材，不覆寫原始最佳版本。評估重點包括預覽以外的用途情境，避免只優化已知鏡位；最終審查應額外查看未當評分起點的角度或姿勢。

實際工具選擇及可用能力仍需核實。付費生成遵守 [產製流程](production-runbook.md)，每筆唯一 operation ID、即時月訂分項與實際扣點另記，不把時間預算轉為花費授權。pending／unknown 必須查原操作；比較工具不會幫忙重送。

## 紀錄格式與判定

將 [實驗紀錄模板](../templates/quality-ledger.json) 保存為 `runs/qa/<request-id>-quality.json`。第一筆必須是 baseline，`parent_id: null`；之後每筆的 parent 是重新計算的當前最佳 ID，不是上一筆被淘汰的候選。不刪失敗輪次或改寫舊分數；更正時保留舊文件並建立可追溯新紀錄。此 CLI 是唯讀核對，沒有 append-only 儲存層，不能防止人手刪改歷史。

每筆欄位：

| 欄位 | 內容 |
| --- | --- |
| `id`／`parent_id` | 唯一版本 ID 與本輪來源版本 |
| `status` | `completed`、`failed`、`blocked`、`pending`、`unknown` |
| `hypothesis`／`change` | 候選的可驗假設與主要修改；baseline 說明原始狀態 |
| `elapsed_seconds` | 實際非負有限秒數，含本輪產製與檢查；不另開紀錄重置原預算 |
| `protocol_sha256`／`reviewer` | 固定契約雜湊與實際檢查者；是來源紀錄，不是自動獨立簽核 |
| `previews` | completed：每個 protocol 視角映射到圖片 `path`／SHA-256 |
| `scores` | completed：每維度映射到整數 `value` 0..5 與具體觀察 `reason` |
| `evidence` | completed：[驗收證據格式](../templates/acceptance-evidence.json)；加 `subject_artifacts`，依 deliverables 順序列出全部模型與已登記相依素材的 path／SHA-256 |
| `failure_reason` | 非 completed：原始原因及失敗分類；不能填造型高分 |

模型、貼圖、BIN、MTL 等都應列入 deliverables／subject；README 等文件不納入品質內容比對。每項檢查的報告須寫明實際檢查的 subject 雜湊與方法；工具只能核對宣告一致，不能讀懂報告或證明檢查曾執行。

```powershell
python -B scripts/workbench.py plan requests/<id>.json
python -B scripts/workbench.py compare requests/<id>.json --ledger runs/qa/<id>-quality.json
```

命令中的 `<id>` 是說明佔位，使用實際需求 ID。結果 `mode: declared_quality_comparison_only`，退出 0 只表示核對完成：

| 結果 | 意義與下一步 |
| --- | --- |
| `baseline` | 有完整申報的基準；可能仍有失敗門檻 |
| `keep_for_iteration` | 每維度不退步且至少一項提高，非美術的所有適用門檻通過；可以成為來源，未必可交付 |
| `keep_for_gate_repair` | 視覺不退步且修復最佳版本原本失敗的必要技術／交付門檻；是門檻修復，不宣稱美術提升 |
| `discard` | 分數退步、無提升且無門檻修復，或已知必要門檻 fail；保留檔案與紀錄，下一輪回到最佳版本 |
| `failed` | 已知失敗嘗試，計入次數與時間；只有新證據／方法才能規劃下一輪 |
| `blocked` | 證據／契約／預算失效或操作未解；停止紀錄後續輪次，不變更產品假裝通過 |

`next_action` 是 `revise_current_best`、`delivery_review`、`stop_budget` 或 `stop_blocked`。單輪／總時間超出、修訂數超出、未知操作、缺少基準或證據失效均無法通過；事後檢查不會取消已發生的花費，也不會實際終止 DCC。協調者必須在執行前核對剩餘預算，失敗、被淘汰的候選也不釋出已用次數。

## 交付門檻與實際證據

最後將 `quality_ledger: {path, sha256}` 加入交付證據，指向上述 JSON，執行 `assess`。有品質契約的需求必須全部維度達到 target、原本美術／技術／包裝及指定環境檢查通過，且交付模型與已登記的相依素材和最佳候選有相同副檔名／內容雜湊。可以把相同內容複製到交付包；重新匯出、換貼圖或增加模型內容需重新比較，不沿用舊分數。

`eligible_for_delivery_review` 仍需要實際查看資產與包內引用、用途情境、來源權利及交付說明。此工具不執行渲染、DCC、評分、依賴圖解析、簽核、付費、Git 或引擎；評分與方法仍屬檢查者申報。圖片與檔案 hash 只能證明內容一致；它們不能證明光照真的固定、背面沒有缺陷或「頂尖」。只有真實模型的前後比較才能證明美術改善。

驗證工具的合成測試與實際資產驗收分開。`tests/test_quality_loop.py` 使用假模型、假圖片與假申報，只測決策和證據綁定；不得拿測試數量宣稱模型品質提升。
