# 專案內 Hyper3D API 入口

`scripts/hyper3d_api.py` 是使用者授權建立的獨立 client。它沿用已安裝的
Windows DPAPI 憑證提供者與受限 HTTPS 傳輸；不修改舊 `authorization.json`、
provider 程式、憑證或舊任務。舊入口的特定任務限制不適用於新 client；新 client
自行檢查工作區路徑、輸入版本、操作唯一性、狀態與成本。

## 啟動

使用 Python 3.10 以上，不需安裝套件；Windows 執行實際 API。請固定 `python -B`，
入口也會在載入 provider 前禁止 bytecode 寫入。預設 workspace 是入口所在 repo；
`--workspace` 可指定本次隔離工作區，所有公開輸入、操作及輸出都必須在該工作區。

```powershell
python -B C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py capabilities
python -B C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py balance
python -B C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py --workspace C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop prepare --spec runs/qa/ro-swordsman-combo-r003/api-spec-v2.json
```

`balance` 只認證及讀取總餘額，不扣點，不證明點數分項或保留額度。
`capabilities` 列出已實作選項與未支援介面，不能當作已實跑生成證據。

## 規格、記錄與付費門檻

prepare 的 JSON 恰含 `operation_id`、`request`（工作區內 requests 檔）、
`images`（assets 內 0–5 張 PNG/JPEG/WebP）、`output_directory`（全新 assets/raw 目錄）、
`parameters`、`authorization`。圖生 prompt 可省略；文生需非空 prompt。
parameters 明確指定 Gen-2.5 tier，可選 Raw/Quad、面數、格式、材質、貼圖模式、
TAPose、對稱、seed 等已驗證欄位；未知欄位拒絕。TAPose 不等於綁骨，Quad 不保證面流。

authorization 記錄既有的人類授權：`spending_scope` 原意、`credit_pool`
（existing_monthly 或 existing_monthly_or_regular）、`no_topup_or_upgrade=true`。
現有 provider 沒有回傳月訂分項，monthly-only 提交保持受阻；使用者已明確授權
月訂／普通現有點數時可使用總餘額。旗標及 JSON 都不是人類授權的替代品。

公開紀錄在 `runs/hyper3d/plans/<operation>.json` 與
`runs/hyper3d/operations/<operation>.json`：需求、品質、輸入、參數及 provider 雜湊，
時間、task UUID、估算／實際 consumed、提交前後餘額、下載檔案大小及雜湊。
餘額差可能包含其他任務，不能充當本任務成本。

合法任務 UUID 會先獨立保存；缺少或無效 consumed 只將 `cost_state` 標成
`unverified_missing_or_invalid_consumed`，保留正常狀態查詢能力，不當作零成本。
若提交後私密狀態寫入失敗，公開 unknown 紀錄仍保留已知 UUID、已核實成本與
`failure_stage`；無法恢復查詢識別時停止，不能重送。

查詢狀態需要服務回傳的 subscription key。它不進 repo，而以 Windows DPAPI
CurrentUser 保存於以下**每次需具體授權的新檔案**：

`C:\Users\IOT\.codex\tools\hyper3d-api\state\<operation>.dpapi`

submit 必須在取得該確切檔案的寫入授權後，才傳入 `--spending-authorized` 和
`--authorized-state-file <完整路徑>`。先測試 DPAPI、exclusive 建立同一檔案的預留狀態、
durable 寫入 pending 公開紀錄，才呼叫付費 API。回覆後只更新這個新檔案，沒有額外
全域暫存檔。檔案包含該任務狀態查詢識別，不含 API 主密鑰。

```powershell
# 僅在上述人類授權與執行環境審批成立後使用
python -B scripts/hyper3d_api.py submit --operation <operation> --spending-authorized --authorized-state-file <已授權的完整路徑>
python -B scripts/hyper3d_api.py status --operation <operation>
python -B scripts/hyper3d_api.py download --operation <operation>
```

既有 operation、pending/unknown 或相同輸入與參數的活躍任務拒絕重送。
沒有服務端 idempotency／exactly-once 保證。送出後斷線、不完整回覆、狀態保存失敗
記為 unknown；只能核對原任務。新秘密檔寫入採 flush/fsync，但不是原子替換；
程序中斷若造成損壞，停止並保留 unknown，不會另扣點重送。
首次 status 至少 5 秒，後續退避到 30 秒。失敗是終止狀態。

下載僅允許全部 job Done，沿用 provider 的 HTTPS、核准 host、公開 IP、TLS、
禁止 redirect；簽名網址僅留記憶體，不帶 Authorization。限定檔名、檔案數及大小，
exclusive `.part`、雜湊及不覆寫；部分失敗保留檔案及 download_partial，
不自動重試或刪除。遇到 stale lock／公開 `.tmp` 或私密檔損壞，人工核對原操作後處理。

下載完成或部分下載後的 `status` 只回傳本機下載紀錄，明確標記
`status_source=local_download_record`、`live_query=false`；不重新查服務、不改寫 journal，
避免把 downloaded／download_partial 退回 complete，或使部分下載誤成可重試。

## 功能界線與證據

現有 provider 固定支援 `/check_balance`、`/rodin`、`/status`、`/download`。
BANG、texture-only、agentic 標示 unavailable_transport；不放寬 allowlist，
也不宣稱有自動骨架／動畫接口。需要擴充 provider 時，先列出全域檔案及確切修改。

服務規格：[Gen-2.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)、
[狀態](https://docs.hyper3d.ai/en/api-specification/check-status)、
[下載](https://docs.hyper3d.ai/en/api-specification/download-results)。估算依當次確認的規格；
實際費用以回傳 consumed 為準。API 成功、downloaded、Blender 技術檢查、美術接受及
指定動畫驗收是不同證據，仍依固定基準與逐項無退步比較流程驗收。

離線測試：`python -B -m unittest discover -s tests -v`。
此文件及程式不授權 commit、push、升級、加購或修改全域設定。
