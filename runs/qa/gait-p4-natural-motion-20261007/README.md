# P4 步態自然度：准入盤點與固定 A/B 條件

狀態：**未完成（受阻）**。工程基準與 baseline 實體已核實；新 baseline 動作觀察、candidate、A/B 美術及 runtime 驗證為 **NOT_RUN**。本紀錄不是動畫改善成品，也沒有開始新 trial。

本次依使用者指定的 gait 工作接續，從 `16344513cb8e6431a0dfcec128fc5c86d351361a` 建立乾淨隔離分支 `codex/gait-p4-natural-motion-20261007`。原 `art-tools-upgrade-20261007` 的 verification、installed-files、工程與 motion plan 全部保留原 bytes；最新基準 CI 的即時查詢另外保存，不回填歷史快照。

## 已完成的必要準備

- 以核准 host context 核實 HEAD 與乾淨 Git 狀態。sandbox 的 `dubious ownership` 是執行身分差異，沒有修改 safe.directory、ACL 或全域設定。
- 只用 `git lfs checkout -- <三個明確檔案>` 從既有本機 cache 還原 b20-coatlie3 master、a04 action 及 a04 baked-owner GLB。沒有 fetch/pull、外部下載或 master 修改；SHA 與既有 QA 相符。
- 用既有 `identity`、workbench request validation 與 GLB inventory 核對 request／quality digest、實體來源與結構。inventory 不代表動畫、外觀、rig 或 runtime 驗收。
- 查過 library、動作來源 catalog、MMORPG 參考清單及製作增補。選擇原 clip 的授權本機修訂，重用凍結程式與新版本資料；沒有匯入權利未知的 motion，也沒有另建通用工具。
- `ab-plan-v002.json` 固定 request、baseline／a04 spec SHA、相機／光照／地面／尺度、正常與慢速、接觸時窗及評估條件。它只凍結補充比較條件，未改 r6 的 quality、anchors、target 或 required checks。原 Frame1 五視角另外保留；0.5／1／1.5 倍速、30／60／120 fps、100／200／400 ms 的完整轉場 gates 仍須照原契約執行。candidate 參數與 trial 身分仍為 null。
- 執行前登記來源雜湊、新路徑、trial、參數及真實開始時間；產物雜湊、結束時間與耗用在執行後登記。v2 修正唯讀審查指出的三個文件缺口，`ab-plan.json`、`preflight-used.py` 與 `verification-v001.json` 保留為 v1 快照。最新靜態核對為 `verification-v002.json`。

## 真實時計的缺口

`v001-pause-31.json` 的 36 筆 interval 合計為 **54,306 秒**，快照時刻為 **2026-10-07 13:58:41 台北時間**。entry 26 只將 v001 單候選上限提高為 129,600 秒；r6 總上限仍為 172,800 秒、候選 4 個，其他候選的標準上限仍為 64,800 秒。

目前無法核實快照後的協調者工作及排除等待區間。原 clock chat `01a114d8-92bf-71a0-b52d-ea4aa005ec0c` 讀取回覆 `Could not determine whether Codex thread ... exists. Unavailable or failed hosts: durable`；以 explicit local host 重查亦相同。已定向查找該 ID 的本機 2026-10-07 session 檔名，未找到，沒有掃描全部歷史。

可讀的工具 chat 只有部分 turn metadata，含一個仍標為 inProgress 的舊 turn，以及 parent/current chat 的重疊時段。這不足以核定全部協調者實際工作時間。r6 ledger 只有 carried baseline（2,641 秒），沒有 v001 candidate 的完整 elapsed entry；它與 pause 快照的計入關係也需要對帳。不能從空缺候選列表、新 branch、工具命令耗時或快照減法推定當前剩餘預算。`clock-audit.json` 保留取得的 metadata 與未知項，不把它們改寫成新的正式 ledger。

## 下一個最小可驗證步驟

由原工作協調者提供或恢復 pause-31 快照後至本次工作起點的實際工作起訖、使用者等待起訖、baseline／v001／total 的計入關係及 trial 身分。取得這些證據後，在新紀錄中補帳並核定剩餘時間與候選數；不改原 pause 或清空失敗。若使用者要變更預算，另存明確授權與原耗用，不把新工作當重置。

時計通過後才執行同條件 fresh baseline：先取得 b20 的逐類簽章，正常／慢速觀察，再選一組可驗證假設與候選參數，保存起訖並以凍結工具產製新版本。knee curve 需與真正重心、支撐與動作觀察一起判定，不能用平滑或數值閉環取代自然度。

## 保留的驗證狀態

| 項目 | 狀態 |
|---|---|
| 指定 HEAD、乾淨起點、baseline payload／SHA、request digest | PASS；本次唯讀核對 |
| 指定工程基準 CI run 37592294921 | PASS；同 SHA 的 Linux／Windows jobs；不是 gait 驗收 |
| GLB inventory | PASS；僅結構清點 |
| 當前 clock、候選身分、總耗用 | UNVERIFIED |
| fresh baseline 動作觀察、b20 category signatures、candidate A/B | NOT_RUN；准入受 clock 缺口阻擋 |
| 新 candidate DCC、transition／foot-lock／runtime 檢查 | NOT_RUN |
| 既有 P4 run-07 | FAIL 保留：126/191；runtime 116/118，18.731347653 µm > 10 µm，D2/G1/H1 不改判 |
| 美術接受、交付、P5、gait commit／push／PR／merge／deploy | NOT_RUN |

沒有新增付費呼叫、全域工具或 hooks。可選 Jev 路由被自動核准審核拒絕，理由是 TypeSafe 外部傳輸缺少具體授權；該動作已停止，改用本機唯讀分析，不需要它才能續作。本次只留下未暫存的盤點與計畫，沒有動畫 checkpoint 或背景 DCC/runtime 程序。
