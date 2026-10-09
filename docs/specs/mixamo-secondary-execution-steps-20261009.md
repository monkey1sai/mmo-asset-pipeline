# Mixamo／次級動態逐步執行清單

依據：既有 `mixamo-secondary-character-workflow-v1`、[最終驗收增補](mixamo-secondary-acceptance-20261008.md)、[第二候選結果](zhaoyun-d1-second-candidate-checkpoint-20261009.md)，以及使用者要求依步驟逐項實作、驗證並完成目標。本清單拆解方法，不改 D0–D5 完成條件，也不授予新候選、付費、外傳或介面變更額度。

2026-10-09 起點：PR17 已合併，main `553109fd6a718dc3be93877c39f3e5d68a5dba98`。兩個真實修復候選均 FAIL；整體 **1/6、NOT_COMPLETED**。每個可獨立驗證 checkpoint 使用隔離 feature → PR → main，人類審查與 CI 各自核對。

| 步驟 | 實際操作與產物 | 放行驗證／停止條件 | 對應 spec |
|---|---|---|---|
| S0 核對基準 | 確認 PR17 合併與 main ancestry、Git dirty、原 GLB SHA，保留兩個 FAIL、來源及時間紀錄；建立隔離工作樹 | main baseline unittest／validate；任何來源漂移停止修改 | D0／全階段 |
| S1 整理共用工具 | 採用既有 secondary solver、request-bound CLI、四類 preset、合成 request；修正小 dt 掛點輸出及未支援的跨鏈 anchor 依賴 | 先重現舊缺陷，再回歸；至少兩種鏈同核；完整 suite、validate、CLI 正／負／邊界、同 SHA CI；只算工程能力 | D4 工程子項 |
| S2 唯讀語義審查 | 由原 GLB 原始 ID 與固定視角，逐區核對身體、衣料、甲片、髮束、繫點；標出外部接縫夥伴、固定配重及錯接嫌疑，列需手工判斷區域 | 不能把骨群、連通塊或顏色當已接受部位；保留多視角、合法骨群、排除區與未確定項。只診斷，不改模型 | D1 前置／D2 |
| S3 有界局部修整 | 依 S2 明確範圍建立新 request／baseline；若確認錯接才修面，確認權重錯誤才局部重配；保護骨架／UV／材質／武器；新 delivery_id | **既有兩候選已用完：第三候選需另行明確範圍與額度。** 固定掛點、三姿勢、完整 idle、新增異常邊、裂縫、抖動與視覺全部過關才採用。任一退步 FAIL，不擴遮罩換參數逃避 | D1／D2 |
| S4 準備 Mixamo 副本 | 在已接受的來源副本整理中性姿勢；移出妨礙辨識的附加部位與武器，保存 ID、transform、還原方式；列檔案／SHA／bytes／權利／傳輸內容 | 本地副本先人工／DCC 核對。**實際外傳另取得該次上傳授權**；登入不代替授權。尚無合格副本時 NOT_RUN | D3 前置 |
| S5 真實 Mixamo 整合 | 上傳核對副本、驗肩肘髖膝、取得合法 walk／run／jump；收據記工具／來源／雜湊；既有 adapter 重定向至 target rig | 骨軸、rest、比例、腳底、root policy、完整矩陣與三動作；不替換骨架／掛點，不公開未知再散布權的動作。缺來源或輸出即 NOT_RUN | D3 |
| S6 真實次級動態與 DCC | 角色 profile 配置披風、剛性裙甲／柔性內襯、長髮、飄帶；固定掛點、活動骨、碰撞代理、reset；bake 與 runtime 設定分開交付 | body／secondary 不重複寫骨；起跑、跑、急停、左右轉、跳落；穿插、尖面、裂縫、抖動 FAIL。全新重匯入驗材質／UV／骨架／動作。新增髮／飄帶骨先確認 target 相容性 | D4 |
| S7 Unity 完整遊戲 | 對同一接受候選，在隔離遊戲副本接入已確認 solver／bake 路線；Jev 僅選擇資源，由真實 Unity 執行器啟動遊戲 | 工程測試與可見走跑跳、轉向、攻擊、格擋、閃避、無雙；固定版本與場景、人類自然觀感、玩法與武器契約。未動作或缺證據不能 PASS；E12 不改 | D5 |
| S8 最終交付 | 來源 master／重建來源標示、執行資產、依賴、clip／runtime 設定、版本／hash／權利、重用範例、回滾及遊戲接受紀錄 | 逐項關閉 D0–D5；只有同一候選 S7 完整通過，才是 spec COMPLETE。中間失敗包不算完整成品 | 全部 |

## 本次實作順序與現況

先執行 S0 → S1，再做 S2。S1 是可獨立進行的工具工程，不能藉此將真實角色 D1 或整體 D4 標成 PASS。S3–S8 依表中前置逐項放行，沒有跳過失敗候選直接接入 Unity 的捷徑。

S0：已核對 PR17 合併與 main；baseline 364 tests PASS、0 skipped，pipeline validate PASS（39 assets／11 operations）。

S1：已重現兩項 solver 缺陷並加入回歸；零 substep 輸出以當前掛點剛性搬移點陣列副本，保留固定步內部狀態與時鐘，新增掛點誤差驗證。另一活動鏈作 anchor 明確拒絕。具體完整驗證結果隨本 checkpoint 的 QA 紀錄保存，沒有拿歷史測試當作本次結果。

S2：待完成真正語義審查；之前 496 頂點面板只是有限工程試驗，不是完整披風遮罩。S3：候選額度為 0。S4–S7：未放行。S8：未完成。整體仍 **1/6**。

## 邊界與承接

本次 S1 工具修正不新增角色候選。角色兩次 FAIL、已用時計、歷史 UNKNOWN 與原始證據永久承接；舊 60 分鐘窗口不因新日期或分支重新啟動。新計畫不默認增加第三候選、Mixamo 上傳或 Hyper3D 點數。

Hyper3D 僅在 S2／S3 證實有必要重建時比較；月訂分項、輸入／參數、operation 唯一性及具體預算核對後才可提交。不能為了繞過局部修復 FAIL 而直接生成整個角色。

每次停止回報：本輪完成的 S 步驟、D0–D5 完成數、實際版本／檢查／PR狀態、FAIL／NOT_RUN、下一個前置及負責人。失敗或授權受阻時交付已完成的獨立成果，不偽稱全部完成。
