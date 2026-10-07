# 2026-10-07 目前成果收斂

使用者要求：「先將目前成果收斂到 origin master上」，查明預設分支為 main 後，使用者明確選擇 `origin/main`。此目錄保存本機準備與確認後的同步範圍；授權見 target-choice.json，實際遠端同步與還原結果以執行收據為準。

## 遠端同步與本批還原

`origin/main` 已正常由 `08c454e` 推進至成果提交 `1ae4f330b2f30ba863785801634e4a803de04b5c`，67 個不同 LFS 物件（約 275 MB）已同步。GitHub 全新 no-checkout partial clone 的 HEAD、origin、endpoint、空 LFS store 與無 local alternates 均已核對。從原始 Git blob 與 LFS 物件還原的 411 個來源檔（341 一般 Git、70 LFS 路徑）及當時 20 個附加收據／attributes，SHA-256 與大小全部符合；独立審查重新核對也沒有差異。詳見 [同步摘要](sync/sync-summary.json)、[還原核對](sync/restore-verification.json)。後續收據提交只新增同步紀錄，不變更成果 payload。

還原時首次普通批次 fetch 因 partial graph negotiation 失敗；依 Git 2.42 官方 promisor 參數，針對當時仍缺少的 419 個選中 blobs 做一次修正後成功。`restore-git-transfer.json` 的 `still_missing: 419` 是修正前快照，還原後沒有缺檔。為避免 Git LFS 3.4 掃描時下載其他 Git blobs，以本機限定 70 個原始 pointer 的 local-only scan commit 作 LFS fetch 輸入；真實 GitHub HEAD 始終為 `1ae4f33`，該掃描 commit 未推送、未替代成果來源。

先前指定的空 hook 目錄被 Git LFS 3.4 filter 自動填入四個標準 hooks，並在第一筆普通 Git push 重查了已上傳物件（0 B/s）。因此不能宣稱整段操作的 hooks 始終停用。後續還原不用 filter、smudge 或 checkout，也未變更 filter.required；新 hook 目錄前後都為空。四個本任務自動建立的暫存 hooks 已核對並移除，原始目錄及事件雜湊紀錄保留；見 [hook 更正](sync/hook-correction.json)。

還原驗證僅涵蓋本批來源檔與上述附加檔，未驗完整歷史、全 repo 標準 checkout／smudge、DCC 或新增 runtime。主工作區的 local main 與原 RO 產製工作區保持原狀；完整收斂成果位於本隔離工作區與 origin/main。

基準為 origin/main `08c454e6c6e7566f7a7625953773b6eb18693f5c`，已包含角色分支 `75b8950` 的既有提交。新增成果從 root 與 `tmp/art-quality-loop` 擷取，共 411 檔、374,533,881 bytes；逐檔來源、大小與 SHA-256 見 source-manifest.json。原始需求、失敗紀錄與產製 bytes 保留，不重製資產或放寬門檻。`.claude/launch.json` 是本機預覽設定，未納入。

準備期間 root 新增提交 `7423acdfda94d62ed455e8ed343da6bc024b6fce`，正好包含原先 37 檔；411 檔原始 bytes 全部未變。原始快照不改寫，狀態變動另存 source-state-update.json。收斂保留這筆提交為 merge parent，不 reset 原始工作區。

## 已執行的本機驗證

- `python -B -m unittest discover -s tests -v`：243 tests，OK；紀錄 unittest.log。
- `python -B scripts/pipeline.py validate`：39 assets、11 operations，valid；只驗 schema、連結與 ledger。
- `checks-used.py`：交付 manifest、P4 manifest、runtime 結果與 runner 雜湊核對；紀錄 integrity-checks.json。
- 營房 assess：證據完整性 valid、eligible_for_delivery_review。沒有重跑 Unity 或作新增美術接受判定。
- 全 411 檔原始 bytes 掃描（含大型與 LFS/binary）：兩筆 signed_url 匹配為相同 float32 二進位片段，94 bytes 中 55 bytes 非 printable，非有效 UTF-8，附近無 HTTP scheme；處置見 integrity-checks.json。沒有在收據输出原始匹配值。此方法不涵蓋壓縮 metadata 或所有圖片隱私判斷。
- Git 一般 blob 與 LFS pointer／本機物件的逐檔 stage 核對，另存提交前紀錄；不能以本機物件存在推論遠端同步成功。

## 仍未完成的工作

- RO Combo a07：collapse 254/671、握持 3 個過渡取樣等 H1 已知失敗維持原判定。
- P4 run-07：runtime 已跑完但 closed-loop FAIL，2/118 blocks、18.731 µm > 10 µm；沒有技術豁免。
- P5 凍結與 holdout 未開始。後續以 `runs/qa/ro-swordsman-character-v1/v001/p4/milestone-04-progress.json` 與最新 authorizations 為準。05:29Z 的 handoff 是歷史快照，當時 pending 的資訊未改寫。
- `tools/glb_bounds.py` 未累積父節點 TRS；有 hierarchy 的模型會得到錯誤的 world bounds。獨立審查的最小案例 parent x=10、child x=1，工具回傳 x=1，正確值 x=11。本批三個交付 GLB 沒有 parent children 或 matrix，該問題不推翻本批已保存的 bounds。後續應支援父變換或拒絕該輸入並加回歸測試。
- 營房視覺可讀性的獨立美術審查仍未完成。

## 同步邊界

origin 已確認為 GitHub 公開倉庫 monkey1sai/mmo-asset-pipeline，使用者選擇的目的地為 `refs/heads/main`。只允許正常 Git 與 LFS 同步本批成果；不 force push、不改 default branch／可見性／配額／hook／全域設定，不進行付費生成、遊戲部署或 P5。remote SHA readback 與隔離還原結果以實際同步收據為準。
