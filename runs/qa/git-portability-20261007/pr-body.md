## 摘要

RO 劍士角色動畫 V1（需求 r6）第三、第四里程碑的工具、資產與證據，皆經數值檢查與使用者美術審查接受（授權第 23、27 筆）。

- **第三里程碑**：Cast a04、LieDown a08、Sleep_Loop a04、GetUp a02 在基礎 b20 上通過片段檢查、runtime 閉環與回讀；基礎 b19／b20 修正；鉸鏈手臂 IK、床面互動與插槽工具。
- **第四里程碑（P4）**：可操作的 Three.js 轉場 QA 場景（`tools/runtime-qa/three/p4.html`）、權重控制器與著地腳鎖定（Python／JS 雙實作，單元測試含 node 比對）、Blender 轉場檢查（r6 `transition_matrix` 關卡）、反例與探針。
  - 轉場矩陣 run-05：164 組通過 115 組。已知失敗依第 26 筆授權（D2、G1）列明，門檻未放寬：皺褶區 collapse 47 組（位置與分類見 `p4/milestone-04-progress.json`）、1.5 倍速腿長極限 5 組。
  - runtime：99 個參考點最大 4.217 µm（門檻 10 µm）；播放／暫停／跳轉 150 次比較差 0；四種注入故障皆被抓到。
- 授權紀錄 `runs/qa/ro-swordsman-character-v1/authorizations.json` 第 16–27 筆；時鐘 v001-pause-15 至 26。

## 驗證

- `python -B -m unittest discover -s tests`：183 項通過
- `python -B scripts/pipeline.py validate`：通過
- 每個 commit 的暫存內容逐位元組核對（`runs/qa/git-portability-2026100[5-7]`）；大型二進位走 Git LFS

## 範圍說明

- 僅供審閱，不在此自動合併；不含連段片段（P3 剩餘項）與 P5 凍結／holdout。
- 被取代的中間輪次依既有做法保留為證據。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
