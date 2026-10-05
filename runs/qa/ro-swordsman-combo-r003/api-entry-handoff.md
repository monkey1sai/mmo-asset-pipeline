# 新版入口與續跑點

## 2026-10-03 實際續跑結果

下方「付費暫未提交／待授權」段落是本次授權前的歷史交接，保留原文，不代表目前狀態。
使用者已回覆「同意授權」該確切 DPAPI task 檔；僅建立與更新此一新檔。
實際任務 `ro-swordsman-apose-20261002-001`／UUID `b51afd35-409d-48e6-b2a0-4c4e0b844904`
於 UTC15:46:36 提交一次，服務回報 consumed=0.5；4次狀態查詢後7個job全部Done，
UTC15:52:38 完成三檔下載；最後非扣點查餘額228。沒有重送、加購或升級。

原始GLB `assets/raw/ro-swordsman-combo/rodin-v002/base_basic_pbr.glb`
SHA256 `da418afbd90bf95d7994e6642460891b0a3e85699713769db7cbaed1a98a4b98`。
檔案11818820bytes，另保存 preview.webp、render.jpg；operation journal保存各檔雜湊。
API入口實際生成／恢復查詢／下載已驗證；月訂分項仍未回傳，不推定分項餘額。

原始固定五視角與全新GLB匯入baseline已完成；39746tri、3張內嵌2K貼圖、0骨架／動畫，
是靜態候選，不能宣稱完整交付。v001保留source座標／UV並建立46bones與獨立劍，
目前實際三姿勢預檢發現衣片／褲腿問題，仍未接受。原baseline時鐘與唯一v001時鐘保留。
過頭長尖刺經邊→rest頂點→原权重追溯，根因為衣片空間包絡侵入9個拇指頂點；
恢復原生手部域後兩條追蹤邊回到約4–6mm，不是「手骨牽動腰帶」。
完整300幀、VFX與最終交付需要變形預檢先通過，不以API成功替代美術驗收。

Git仍未stage／commit／push。新入口當下沒有任何待處理付費生成。

## 授權前歷史交接

最終狀態補記：獨立28圖複核為NO-SHIP，分數3/3/2/3/2/0，比例從baseline3退為2。
v001總實作／檢查3595.547638秒；phase含baseline共7813.546379秒，原時鐘未重置。
唯一候選計數1/1，compare為discard/stop_budget，assess保持not_ready。
完整300幀／VFX未製作，因實際腕掌／拇指與硬甲保形預檢失敗；不能延展成通過動畫。
最終root112/1.816s、隔離116/1.821s、API23故障測試，catalog39格式有效。
入口下載狀態回歸已先重現後修正，獨立複核包含HTTP302部分下載、拒絕重試、零私密讀取／transport；
downloaded／download_partial重查僅明確回傳本機紀錄，沒有退回complete。

以下繼續保留授權前歷史：

根 repo 入口：`C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py`。
隔離工作區相同版本：`scripts/hyper3d_api.py`。
新版入口自行核對工作区输入、参数及操作，不使用舊 generate 的趙雲／單一任務路徑授權。
provider 程式、舊 authorization.json、舊 state 均未修改。

非扣點 root 實測 2026-10-02T15:37:23.915663+00:00：authenticated=true，balance=228.5，charged=false。
root111 tests/1.851s exit0；隔離115 tests/1.853s exit0；新API22故障案例；catalog39 schema valid。
獨立 reviewer 已重現並關閉 P1：合法 task UUID 必須先保存，成本缺失不能丟失追蹤；
私密保存失敗的 unknown 保留 UUID／已知成本／failure_stage，不能以新ID或seed重送。

既有 `generation-prepared.json`、入口拒絕紀錄及前兩階段失敗／品質 ledger 保留。
新 payload 在 `api-spec-v2.json`，已離線準備為
`runs/hyper3d/plans/ro-swordsman-apose-20261002-001.json`。
選擇 High/Quad18k/TAPose/symmetric/PBR-high/GLB/front-label/seed3417；圖生省略 prompt，
依中性設計圖重建，不再沿用舊victory姿勢。預估0.5，但 actual consumed 以服務回覆為準。
Quad與TAPose只改善生成條件，不保證綁骨、手指／衣襬分離或可接受動畫。

**付費暫未提交。** 使用者已明確授權按需使用現有月訂或普通點數，沒有再次詢問點數。
待使用者授權一個新 global task 檔：
`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-swordsman-apose-20261002-001.dpapi`。
只 exclusive 新建該檔與同檔內部更新／讀取，無 global temp、不含API主密鑰。
此 gate 來自使用者最新指示：repo 外修改列出確切檔案與必要變更，讓使用者授權。

取得這項授權後，先重新核對 plan/input/provider hash、既有 operation 和 output collision；
遵守執行環境自動審批。第一次 submit 會先證明 DPAPI、預留該新檔、fsync公開pending，
再做單次付費呼叫。unknown 只核對同任務，沒有自動重送。submit後至少5秒，
以5/10/20/30秒退避追蹤；全部Done才下載。下載後建立原始版固定視角baseline，
再依 Blender specialist 步驟調整，做骨架、連段、早期GLB重匯入及300幀功能驗收。

baseline clock 仍是 `phase-start.json` 的原始2026-10-02T14:49:27.333812+00:00，
没有偷偷重設。新入口建立／等待授权的时间必须如实记入或作为独立工具工程说明；
若原 trial／phase 時間超出要求，保留失敗／受阻紀錄，不能回寫為有效品質PASS。

目前沒有背景生成工作；未stage／commit／push，等待使用者驗證成果。
