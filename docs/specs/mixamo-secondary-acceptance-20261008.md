# Mixamo／次級動態 spec 執行與最終驗收增補

日期：2026-10-08。狀態：EXECUTING，整體 NOT_COMPLETED。

本增補依使用者最新指示，補充 `mixamo-secondary-character-workflow-v1`，不降低原始需求、測試、來源權利、保護介面或品質門檻。原始完整 spec 與實物目前保留在本地美術隔離工作區；本文件不宣稱它們已公開或已合併。

## 目標與新增授權

以趙雲完成可重用的 Mixamo 身體綁骨／走跑跳與披風、裙甲、長髮、飄帶次級骨鏈工作流。角色差異由設定、映射、語義遮罩與局部美術修整表達，不修改共用核心。

使用者同意開始修復與整合，要求每次回報 spec 完成度、每個可獨立驗證的進度 checkpoint 經 PR 合併 main，以及最後開啟 Unity、使用 Jev 參與遊戲執行流程，全部必要測試通過才算完成。

- Git 目的地：`monkey1sai/mmo-asset-pipeline`，feature branch → PR → main。已授權必要的 commit、非 force push、PR 與符合審查條件的 merge。每個 checkpoint 對應一個可審查主題，未通過的實驗不因存在進度而接受。遵守現有 human approval／protection，不能偽造 approval 或繞過 checks。
- Unity 目的地：changshan-longdan 的隔離驗收副本。授權本地開啟與執行測試；原始遊戲工作區及正式資產維持保護。必要候選接入先核對遊戲契約，runtime 求解器改動須列具體差異與影響，不能由這次驗收要求推論為任意遊戲改寫。
- Mixamo 每次模型上傳仍先列檔案、雜湊、權利、用途與外傳範圍，取得該次授權。Hyper3D 仍受已授權月訂來源與具體操作預算限制。
- 不授權部署、加購、升級、刪除既有證據、覆寫 master、一般全域修改、修改已耗盡兩輪預算的 E12 量測器或公開未知再散布權的來源素材。

## 階段及完成度計算

每次交付逐項報告階段狀態與可定位證據。只以符合整個階段必要條件的 PASS 計入完成數；部分實作、FAIL、BLOCKED、NOT_RUN、UNVERIFIED 不算完成。完成度以「已完成階段／6」表示，不用檔案數、測試數或估計百分比代替。

| 階段 | 必要完成條件 | 目前狀態（既有本地證據快照） |
|---|---|---|
| D0 診斷與基準 | 原 GLB 雜湊、原始 ID、全矩陣與異常區域、獨立 Blender 重現、原材質 UV 骨架保留 | 已有完整局部診斷；CPU／Blender 對照通過，形變 FAIL；診斷階段結案檢核待核對 |
| D1 修復候選 | 既有 trial／time 可核對，視覺確認語義遮罩，單一假設，新版候選與同條件比較 | 未完成；骨影響 seed 誤分類靴子，不能直接用於拆件／配重；歷史時間缺口保留 |
| D2 製作路線 | 完成必要局部修整；確有重建需要才用 Hyper3D，合法输入／月訂成本／operation 可核對 | 未完成；總餘額不證明月訂分項；若不需要生成，以有證據的 NOT_APPLICABLE 決策結案，不假稱生成 PASS |
| D3 Mixamo 整合 | 審查中性上傳副本、逐次外傳授權、真實綁骨與走跑跳、adapter fixture 與真實 target rig 重定向通過 | NOT_RUN；登入／工具存在不是完成 |
| D4 製作端接受 | 四類 preset、至少兩種鏈共用核心、完整動作與視覺、重新匯入材料 UV 骨架與掛點一致、來源／交付完整 | 部分工程實作；合成 fixture 材料一致性 FAIL，真實角色接受 NOT_RUN |
| D5 Unity／遊戲接受 | 同一候選及 solver 接入版本，Unity 可見執行、必要自動測試與全部指定玩法場景、自然觀感與人類審查通過 | NOT_RUN |

目前正式完成度：0/6（階段結案尚未逐項確認）。此數字不否定既有工具與診斷成果；它避免把部分檢查換算成整體完成。

## Jev 與 Unity 的實際責任

已核對本地 Unity 專案 `ProjectSettings/ProjectVersion.txt`：6000.6.4f1；同版 Editor 目錄存在。尚未在此 checkpoint 執行 Unity 或確認專案可載入。

現有 Jev MCP 是 advisory Choice／角色與資源選擇，不啟動 Unity、不操控遊戲、不授予測試 PASS。最終流程須使用實際可用的 Unity 執行器（Editor／測試 runner／遊戲操作工具），由 Jev 在有充分且可外傳的去敏背景時參與資源或驗收步驟選擇，再由主控執行。記錄 Jev 真實結果及 observation outcome；不得將 status／confidence／路由建議寫成遊戲已執行。

若缺少可用 Unity 操作渠道、Jev 出錯或缺少完整玩法證據，D5 保持未完成。不得聲稱已建立不存在的 Jev→Unity 自動控制 API，也不修改全域配置來偽造整合。

## 最終完成閘門

必要工程檢查：`python -B -m unittest discover -s tests -v`、`python -B scripts/pipeline.py validate`、新增工具正負面與邊界測試、適用 Node 測試、同 SHA 的遠端 CI。缺依賴、skipped、missing 不算 PASS。

必要實物檢查：fresh import → bind-only → 固定 idle → 站立、起跑、持續跑、急停、左右轉 → 跳躍、落地。權重、完整蒙皮、全部異常區域、短邊絕對伸長、固定掛點、穿插、抖動、回彈、朝向、單位、root motion、匯出重新匯入逐項保存。大片尖三角、裂開、跨部位拉伸、持續數值抖動即 FAIL。

Unity 另驗攻擊、格擋、閃避、無雙及遊戲契約要求的完整場景；保護武器握持、掛點、tip／tipBase 與玩法。自然觀感、人類感受、自動測試、DCC、runtime、release 是分開證據。GLB 不含可自動執行的風／彈簧／碰撞求解器。

只有 D0–D5 都結案、所有適用必要測試與審查 PASS、合法來源與交付可還原，且遊戲端接受同一資產／runtime 版本，才能標記 spec COMPLETED。路線不適用須由具體證據結案，不把必要 Mixamo 或 Unity 驗收改為選用。

## checkpoint 交付規則

每次回報包含：本次完成的 spec 條目、階段完成數、最新測試命令／版本／證據、已知 FAIL／NOT_RUN、PR URL／base／head／CI／review／merge 狀態，以及下一個必要步驟。PR 只包含本主題且具公開權利的內容。原始／失敗／歷史證據保留本地，不擅刪。

原模型 SHA-256：`7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33`。此公開文件不包含模型、貼圖、動畫、私人登入資料或完整診斷快照。

新分支、spec、request 或 ledger 不重置既有 trial／time／修訂預算。若歷史預算無法核對，保留缺口並繼續已授權、不依賴它的診斷與工程工作；不能事後補造耗時以放行修訂。
