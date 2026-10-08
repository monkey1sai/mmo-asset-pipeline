# 專案影片技能

依使用者指定影片 https://youtube.com/shorts/4zI2oP70aWs ，將適用技能接入需求驅動的美術工程流程。上游完整技能以固定 commit 的 project-local Git submodule 保存，保留原有 helpers、參考資料與授權。

| 技能 | 用途 | 固定版本 | 授權 |
| --- | --- | --- | --- |
| video-shotcraft | 素材展示、分鏡、運鏡、字幕及 Remotion 動效 | 5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab | 程式 Apache-2.0；音訊依 assets/audio/ATTRIBUTION.md；Remotion 授權另計 |
| video-use | 剪輯既有 Blender／遊戲錄影、時間軸及剪接自檢 | b877063835e6ea6e457124da7e28a0ae26691dc3 | 程式 MIT；ElevenLabs 轉錄另外核對帳戶及花費 |

來源：https://github.com/Vincentwei1021/video-shotcraft 、https://github.com/browser-use/video-use 。

影片另介紹手繪故事、OpenMontage、MoneyPrinterTurbo，本輪未安裝：分別偏向手繪敘事、完整製片系統及庫存素材批次影片，需求需要時再評估。

## 在本機還原

從 repo 根目錄執行（PowerShell／bash 都適用）：

```text
git submodule update --init --checkout -- .agents/skills/video-shotcraft .agents/skills/video-use
git submodule status
```

只取得固定版本，不使用 --remote、submodule git pull 或未固定的 npx skills add 覆蓋本安裝。不安裝全域技能，不修改其他專案或 ChatGPT 個人技能。

video-shotcraft 的 Remotion 模板依上游 lockfile 安裝：

```text
cd .agents/skills/video-shotcraft/template
npm ci --ignore-scripts --no-audit --no-fund
```

需要 Node／npm，按上游文件核對當前相容版本；實際渲染另外需要 Chrome Headless Shell。上游依賴 lifecycle 不在安裝時自動執行。

video-use 需要 Python 3.10+、ffmpeg、ffprobe。從其技能目錄建立隔離 venv：

```text
cd .agents/skills/video-use
python -m venv .venv
```

Windows：`.venv\Scripts\python.exe -m pip install -e .`；Linux／macOS：`.venv/bin/python -m pip install -e .`。不更動全域 Python。沒有 ElevenLabs 憑證時，語音轉錄保持 NOT_RUN，不要求使用者貼金鑰進聊天或 repo；沒有台詞的剪輯可用來源時間碼建立 EDL，先核對 helper 對該來源的支援，不冒稱語音流程已執行。

## 製作流程

1. 先讀 $art-engineer 的需求、來源與品質契約，取得已授權的真實 Blender／runtime 預覽；未完成的 rig／動作先處理模型本身。
2. 動效分鏡讀 video-shotcraft/SKILL.md 與所選模式的 pipeline／模板，再讀實際鏡頭卡和 demo。剪輯讀 video-use/SKILL.md、install.md 及實際 helpers，核對來源音軌、fps、HDR、長度及字幕需求。
3. 現有使用者指示與 repo 的 Git、憑證、花費及素材規範優先。上游的貼金鑰、全域安裝、主動發布或作者推薦不擴張本任務；已有具體剪輯授權時沿用，共同創作仍缺方案時依上游流程確認。
4. 來源與製片工程保存於 runs/qa/<request-id>/footage/；video-use 產物放其下 edit/，不寫進技能 submodule。最終包依既有資產規範歸檔 deliveries/。
5. 用 ffprobe 核對成片格式、fps、長度；抽查首尾與剪接點、聲音量測及字幕遮擋，正常／慢速播放檢查動作，依上游成片流程做獨立終檢。未聽音、DCC 或 runtime 實測時明列缺口。
6. 完整、正常速度、無遮擋的驗收原片與宣傳剪輯分開；不以剪接掩蓋穿模、腳滑或斷動作。MP4 不等於可遊玩的 GLB／FBX。既有 assess 不支援影片時另存證據，不宣稱影片已經 assess 通過。

使用範例：「用 $video-shotcraft 把這份角色的 Blender 預覽製成 15 秒展示片，採自主自由創作，保留正常速度完整攻擊段落。」或「用 $video-use 剪輯這個資料夾的演示錄影，先整理方案。」

## 驗證狀態

本次 PR 的驗證紀錄在 runs/qa/video-skills-pr-20261008/verification.json。上一輪暫存產物已無法取得，先前測試結果只能作歷史參考，不取代本次 CI 或實測。技能版本登記、相依安裝、實際渲染、美術品質與遊戲 runtime 分開回報。合併 PR 後仍需在使用者電腦初始化 submodule 及安裝依賴。
