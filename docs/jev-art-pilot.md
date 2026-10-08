# Jev 中文遊戲美術需求試點

此試點依使用者 2026-10-07 同意的「需求分類＋素材候選重排」建議建立。範圍為 12 類遊戲、20 筆中文需求、每案 4 個素材候選；最多 20 次 Jev 推論。沒有模型、圖片、動畫或 Hyper3D 生成，沒有遊戲接入、提交或遠端發布。

## 資料與來源

- `tools/jev-pilot/zh-game-cases-v1.json`：Codex 預先編寫的合成需求、素材條目與預期標籤，尚未人類覆核。遊戲類型包括動作 ARPG、MMORPG、射擊、生存、策略、塔防、療癒農場、競速、解謎平台、Roguelike、卡牌與恐怖冒險。
- 28 個合成素材摘要只有測試 metadata，沒有實體模型。另引用本庫 5 個版本的 metadata，保留未完成 QA 與既有接受範圍；本次未檢查實體模型，也未改素材庫。
- `requests/examples/jev-pilot/`：沿用 `make_draft()` 建立的 20 份合法需求草稿，保留中文原文、`draft` 與 `review_existing`。它們由預期標籤建立，不是 Jev 分類結果。資訊不足與 2D 範例的 `static_prop` 僅維持草稿結構，須先澄清或移交。
- 外部 MMORPG 清單已查閱，本次使用本庫 metadata 與自編合成資料，不複製外部程式碼或素材。

## 採用方式

沿用 `scripts/workbench.py` 的需求草稿、素材索引與結構驗證；沿用 `scripts/identity.py` 的路徑與雜湊。模型傳輸使用本機已安裝的 `jev/client.py`，透過 `--client-source` 明確指定，依已讀版本 SHA-256 鎖定，不複製客戶端、不增加依賴。客戶端在內部解析憑證，試點不取得或輸出 key 值。

新增工具只負責準備案例、組合 TypeSafe 問題、比較 baseline 與保存證據。既有 `intake`、`search`、`plan`、`assess`、品質與生成流程不變。

每個案例以一個 request 同時詢問互相獨立的問題：

1. `Choice` 分類：四種現有任務類型，另加 `needs_clarification` 與 `out_of_scope`。
2. `Choice` 選候選：四個素材 ID 加 `none`，不強迫選素材。
3. 每候選一個 `Score`：同一組 0–4 語意符合度錨點，供排序；分數不是美術品質或技術通過。

輸入白名單只有中文需求、遊戲類型、素材 ID／名稱／標籤／描述／限制與問題。不傳預期標籤、原始碼、完整 QA log、模型檔、路徑或憑證。候選集合由 Codex 預先設計，沒有宣稱代表全庫檢索。

## Baseline 與評估

- 分類 baseline：既有 intake 的 `static_prop` 預設；它沒有語意分類能力，因此結果只作功能缺口對照，不宣稱 Jev 改善了既有分類器。
- 檢索輔助觀察：記錄把完整中文原文送進既有名稱／標籤精確比對的結果。
- 排序 baseline：對同一候選集合，以中文二字組 Jaccard 字面相似度排序；Jev 不能取得額外候選或預期標籤。
- 指標：分類符合預期數、素材 Choice 符合預期數、17 個有相符候選案例的 Top-1／Top-3／MRR、3 個需 `none` 案例、0.8 待覆核標記、實際模型版本、token 用量及每 request 延遲。
- 0.8 未經本領域校準；低信心、範圍外、需澄清或 `none` 一律標待覆核。沒有自動套用需求、素材、製作路線或驗收結果。
- 估算價格引用官方 models 頁的 Jev 1.13.0 每百萬 input tokens USD 0.042、output 免費。只有回覆模型符合這個版本才估算；實際帳戶扣款仍未核對。

## 執行

```powershell
python -B scripts/jev_art_pilot.py prepare --run-id jev-zh-pilot-20261007
python -B -m unittest discover -s tests -p test_jev_art_pilot.py -v
python -B scripts/pipeline.py validate

# 本次使用者已同意小量 Jev 試點；此命令會呼叫外部服務。
python -B scripts/jev_art_pilot.py live --run-id jev-zh-pilot-20261007 --execute --client-source C:/Repos/jev-systemone-lab/jev/client.py --limit 1
python -B scripts/jev_art_pilot.py live --run-id jev-zh-pilot-20261007 --execute --client-source C:/Repos/jev-systemone-lab/jev/client.py --limit 20
python -B scripts/jev_art_pilot.py report --run-id jev-zh-pilot-20261007
```

`prepare` 離線、不讀憑證。它不覆寫既有草稿或已準備的 run。`live` 必須同時有 `--execute`、已核對的 client 與凍結 manifest；每案例先保存唯一 operation，再送出一次。成功案例在續跑時略過；任一 prepared／failed／unknown 操作停止整次續跑，不自動重送。先處理原操作與既有用量，再由新授權範圍決定新 run，不能以新 ID 清掉失敗。

HTTP redirect 禁止；socket timeout 20 秒，不宣稱是嚴格的整次 wall-clock 上限。例外只保存錯誤類型與 HTTP 狀態，不寫 provider error body。回覆需通過 Choice／Score 型別、候選範圍、概率和、分數加權一致性與 usage 檢查，之後才計入已評估案例。

## 證據與完成限制

`runs/evidence/<run-id>/` 保存輸入、baseline、凍結雜湊、Authorization Envelope、operations、去敏回覆、`report.json` 與同源 `REPORT.md`。每次呼叫前重新核對輸入；報告重算時核對回覆雜湊與輸入關聯。測試使用假 provider，不能替代 live API 結果。

本次可驗證的是有界文字判斷試點與比較工具。合成案例、單次抽樣、未經人類覆核的預期標籤，不足以證明真實委託準確率、美術品質、動畫、引擎驗收、全庫搜尋或總成本節省。正式採用前以真人需求與盲測資料重新評估。
