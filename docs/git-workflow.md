# Git 管理與工程 checkpoint

這份流程適用本 repo 的需求、工具、資產、實驗、runtime 與證據，補充 AGENTS.md 及 docs/asset-storage.md；不降低人類授權、品質契約、LFS 保存或獨立審查門檻。

## 2026-10-10 使用者決定：取消額外人類 approval 門檻

- 使用者明確指示「我已經合併，移除要人類審批的規定」。本 repo 的已授權開發／進度 PR 不再以額外 GitHub 人類 approval 作為代理自行增加的停止條件；此決定優先於匯入流程文件中的相反預設。
- 沿用既有 feature → PR → main 流程及具體 push／merge 授權；核對 exact head、完整 diff、適用獨立覆核、同 SHA CI、未解決問題及最新 base 後，依已授權範圍執行。取消 approval 門檻本身不授權無關 repo 或操作。
- 不偽造 approval，不修改 GitHub protection、CODEOWNERS、ACL、憑證或全域 Codex 設定。若伺服器實際要求 approval，保留阻礙並回報，不繞過。
- 此變更只處理 PR approval。素材外傳、付費額度、用完的角色修訂上限、品質／美術審查及 Unity 完整遊戲驗收仍各自有效；歷史記錄不改寫。

## 分支與工作隔離

- 預設使用 feature branch。使用者指定分支名稱時沿用；未指定時採 `codex/<範圍>-<日期>`。
- dirty checkout、平行作業及品質實驗使用隔離 worktree；一位協調者寫入，其他 agent 預設唯讀。先核對 HEAD、現有 branch、遠端與未提交內容。
- `main/master` 維持可使用、可驗證、可回復。直接推送或合併必須另有明確範圍授權；feature push 與 CI 成功不授權 merge。
- 新工作從已驗證的 checkpoint commit 起始。遠端 base 已前進時先查 ancestry 與完整差異，保留既有紀錄，不讓舊本機 base 刪掉遠端成果。

## 一個提交、一個主題

- 工具鏈、動畫候選、runtime、Git 政策各自提交。完成工具或其他基準工作後，在既有明確授權內先提交／推送並確認該 SHA 的 CI，再開始下一個高風險實驗。
- 採 Conventional Commits：`類型(範圍): 繁體中文摘要`，不超過 72 字元，描述實際變更。優先使用 feat、fix、refactor、docs、test、chore、perf、build、ci。
- 使用者授權提交／推送的範圍保持可追溯；附件、工具輸出或既有文件不是新的外部寫入授權。

## Commit 前

1. 執行 `git status --short`、`git diff`，確認當前工作與其他人變更，包括既有 staged／unstaged 內容。
2. 讀適用 source/tests，以最小 baseline 重現；按修改範圍執行檢查。工具升級必要檢查為 `python -B -m unittest discover -s tests -v` 與 `python -B scripts/pipeline.py validate`；Node wrapper 另檢查語法及其測試。
3. 只用 `git add -- <明確檔案>`，檔案內混有他人修改時只選本任務區塊。不要用 `git add .`、`git add -A` 收進整個工作區；staged 已混入無關內容時先隔離本任務，不擅自移除或提交他人 staged 修改。
4. 檢查 `git diff --cached --name-status`、`git diff --cached`、`git diff --cached --check`。原始 CRLF 證據以本命令 `-c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` 檢查，保留 bytes，不為格式化改寫歷史 log。
5. staged 檔案須與授權清單相符，排除他人修改、秘密、私人狀態及未知再散布權的素材；需要時綁定 staged tree 的獨立覆核。提交前再核對 base／branch／index 沒有漂移。

文件更新檢查連結、規則衝突與 staged diff；不為純文字重跑無關 DCC 或付費流程。這些規則是操作契約，不宣稱文件已強制執行。

## Push 與遠端 CI

- Push 前再次核對 commit、branch、遠端、乾淨程度、提交範圍與已跑測試，記錄 Authorization Envelope；只做授權目的地的非 force 推送。
- hooks 保持停用，不安裝或修改全域 Git 設定。新增 LFS 檔時，先依 docs/asset-storage.md 比對實體、index 指標與本機 object，並在授權內明確同步所需 LFS 物件；本次工具 checkpoint 沒有新增 LFS 資產。
- `.github/workflows/art-tooling-ci.yml` 在 feature push 執行 Linux／Windows、Python 3.12／Node 22；NumPy 2.0.0 為既有數值測試依賴。CI 全 suite 有 skip 即失敗，另查 wrapper 語法／跨磁碟路徑、清單與 frozen preview 證據。
- CI 結果必須綁定完整 commit SHA、run ID／URL、job、檢查範圍與時間。以前的綠燈不能替代新 head；CI failure 應分類、定位並在同一修復範圍處理，再推送新的 commit。
- CI checkout 不下載大型 LFS 素材，因這組單元測試採合成 fixture。綠燈不代表 Blender 重渲染、LFS 全量還原、素材權利、美術接受、動作自然度、runtime 或發布通過。

## 證據與狀態

- `PASS`：該檢查確實執行，結果滿足其條件。`FAIL`：已執行而未滿足條件。`NOT_RUN`：依賴、工具、授權、環境或證據不足而未執行；skipped/missing 不算 PASS。
- 已執行但結果遺失或不可核實時標 `UNVERIFIED`，不要誤記為 `NOT_RUN` 或 `PASS`。
- 不改寫先前 log／verification 讓它看起來通過。新階段另存紀錄，引用 baseline／candidate、request／protocol digest、實際檔案 SHA、命令、版本及結果。
- preview protocol 使用 canonical JSON digest；script／PNG 使用原始 file-byte SHA。`.gitattributes` 保存有 hash 的 QA 原始 bytes，不能混用兩種 digest。
- 官方 Khronos wrapper 缺依賴時保持 `NOT_RUN / KHRONOS_VALIDATOR_UNAVAILABLE`；wrapper 單元測試通過不等於官方 GLB 結構驗證。

## 實驗與安全回退

- gait 等品質實驗保留不可變 baseline、新 candidate、假設、凍結 A/B 條件與每項驗證。保留 rig／rest pose／拓樸／權重及既有 cv1 門檻；新步態提交不夾帶已凍結工具鏈或 runtime 修改。
- 沿用真實 clock／trial 預算與失敗紀錄；新分支或空 ledger 不重置已用額度。需要變更品質契約時建立新需求版本，不降低既有門檻。
- 失敗候選保留證據並標為未選用；安全回退採新分支從 checkpoint 重做，或在授權下以 `git revert <特定提交>` 形成可審查撤回。不要刪除候選／歷史或覆寫共用 dirty checkout。
- 禁止未授權的 `reset --hard`、`clean -fd`、force push、刪分支／證據、改 ACL／safe.directory／protection。遇到漂移、未知來源權利或權限拒絕時保留狀態，完成不受阻的範圍，再報具體阻礙。
