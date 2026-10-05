# r010 驗證索引

本階段為使用者明確授權的「設計握姿與必要形變修正」。原quality標準、原五指完整遮罩、
frame31握持建立時刻、1µm回讀容差及r008/r009歷史保持。完整交付仍NO-SHIP。

## 直接查核

| 紀錄 | 內容 |
|---|---|
| `local-contract.json`、`phase-start.json` | 保護域、門檻、310歷史SHA與原時計 |
| `baseline/local-baseline.json`、`pad-normal-audit.json` | 原握持缺失及完整指腹法線 |
| `v001-authored-controls/` | 較深彎曲失敗：28交叉／1.955mm穿入 |
| `v002-pulp-corrective/` | 整片指腹修形失敗：食指僅2點；含線框及相鄰梯度 |
| `v003-index-pulp/` | 原pad接觸全3点；灰模與場邊界仍須美術判斷 |
| `v003-local-animation/` | 原121樣本射線FAIL、原NPZ點陣列、五固定動畫時刻PNG |
| `v004-certified-animation/` | 原射線＋補充分類、單clip、完整權重映射及匯出校正 |
| `v004-fresh-glb-attempt2/result.json` | 原權重略去造成7.895µm誤差，FAIL保留 |
| `v004-fresh-glb-attempt3/result.json` | 校正後121時間點／1µm容差通過 |

`interval-events.jsonl`保存各實際時間點與原／補充分類；有界檢查不是連續體積或連續時間證明。
`exact-weights-all-IDs.json`保存全部1106匯出點到904原ID的前後權重和L1，非只抽20例。
新增微小權重109個原ID影響此前被略去；其他112個ID差異還包含浮點正規化。
後處理只改1686個JOINTS_0/WEIGHTS_0 payload bytes，不改Basis、UV、morph、骨、動畫或安装工具。

## 已知未通過範圍

原16跨UV島面與材質、握姿美術、左手及全角色衣甲、300幀技能與VFX仍未驗收。
數值接觸每指3點不替代包握輪廓。獨立灰模審查未接受美術，整个local functional gate未通過。
完整baseline與其原分數保留，局部數值／匯出成果另外記錄。
品質帳使用fullquality failed表示尚未滿足原委託，不表示校正後的局部技術檢查失敗。

`independent-final-review.md`為本次Astra/high唯讀審查的完整回覆，不是人類批准。
其限制含自交排除相鄰/相切/共面、有限穿入採樣，以及劍closed/oriented檢查未涵蓋自身全交叉。

最終比較、assess、成本／時間、完整性檢查及獨立審查於本目錄另存，依實際檔案結果為準。
時鐘包含準備、測試、等待與審查；首個可觀測時刻之前的準備時間未知，沒有補造。
新增API／點數0；沒有repo外寫入。commit、push等人驗證；未宣稱LFS上傳或clone還原通過。
