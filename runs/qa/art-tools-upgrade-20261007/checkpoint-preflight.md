# 工具升級 checkpoint 準備

本紀錄接續原始本機驗證，不覆寫 `verification.json`、原始測試 log 或 Blender capture。

- 使用者於本次對話授權：只提交工具升級與相關 QA，推送專用 feature branch，驗證遠端 Python／Node／路徑 CI；CI 成功後才開獨立 gait P4 工作。
- Feature branch：`feat/art-engineer-tooling-upgrade-20261007`。
- 提交父版本：遠端 main `cc5644e5ac8c10a01815b52ad7d78bd03adc8352`。原本機工具 smoke baseline 為 `1ae4f330b2f30ba863785801634e4a803de04b5c`；兩者之間只有既有收斂同步證據，全部保留。
- 提交範圍：來源紀錄、固定 Beauty／Clay 預覽、GLB wrapper、測試、模板／文件、既有本機 QA、CI 與證據保存屬性。`motion-baseline-plan.json` 是既有唯讀盤點，不是新的 gait trial。
- 排除：`.claude/`、新的 gait／動畫資產／runtime 修改、付費生成、全域安裝、main 推送、PR／merge、hook 或權限修改。
- CI：Linux 與 Windows，Python 3.12、Node 22、NumPy 2.0.0（與本機已驗版本一致）；完整 suite 有任何 skip 即失敗，另檢查 Node wrapper／Windows 跨磁碟邊界、清單與原始 preview hash。
- Checkout 不下載 LFS：單元測試使用合成 fixture，清單驗證只需既有文字證據；歷史 Blender 圖片 SHA 在 CI 回讀，CI 不冒稱重新跑過 Blender。
- 官方 Khronos 結構驗證仍為 `NOT_RUN / KHRONOS_VALIDATOR_UNAVAILABLE`。CI 不安裝該依賴，也不把 wrapper 測試改稱官方資產驗收。

## Authorization Envelope

- Destination：`git@github.com:monkey1sai/mmo-asset-pipeline.git`，公開 repo 的上述 feature branch 與 GitHub Actions。
- Purpose：建立可追溯的工程 checkpoint，取得與提交 SHA 綁定的遠端測試結果。
- Allowed operations：指定檔案 stage／commit、非 force feature-branch push、由 push 觸發 CI、讀取 run／job／log 與 refs。
- Data being transmitted：經審查的 repo source、測試、文件與本機 QA 證據；CI 取得相同公開提交及公開工具依賴。
- Forbidden operations：憑證／私人來源／`.claude/`、新 gait trial、main／master push、force、merge、部署、全域設定／ACL／hooks 修改。
- Stop conditions：base／branch 漂移、非範圍 staged 內容、秘密／未知原始素材權利、CI failure 或 missing、認證／網路／自動審查拒絕。CI 未完成前不開 gait 工作。

本文件只記錄提交前條件。實際 commit、push、遠端 run 與新的工程基準以後續 checkpoint 紀錄為準；未取得遠端結果前不宣稱 CI PASS。
