# MMORPG 開源倉庫參考清單（給 AI 與美術工程師）

使用者於 2026-10-05 指定此份報告為美術開發的重要參考資源，目的是避免重新造輪子。製作或設計前，先在這裡找可重用的資料、方法與命名，再決定自製。

- 原始報告：[MMORPG_GitHub_Source_Report_20261005.pdf](MMORPG_GitHub_Source_Report_20261005.pdf)
  - 3 頁，220,326 bytes
  - sha256 `11e5aca0ab4db13092edee66ae1a7d71677b983b31c5801d60189be5eeebbf40`
  - 複製自使用者本機 `C:\.llmcode\output\pdf\`
- 報告的本機證據不在本 repo：`C:\.llmcode\mmorpg-github-forks-20261005`
  - 檔案：`RESULT.md`、`source-manifest.json`、`evidence/summary.json`、`native-verification.json`、`mirror-verification.json`、`delivery-review.md`

## 倉庫一覽（報告原載數據）

全部是使用者帳號 `monkey1sai` 下的公開倉庫：9 個 GitHub fork，加上 3 個從 Bitbucket 複製的 L2J 鏡像。

| 遊戲／專案 | 倉庫 | 上游 | 預設分支 | 分支 | 標籤 |
|---|---|---|---|---|---|
| RO／rAthena | [monkey1sai/rathena](https://github.com/monkey1sai/rathena) | rathena/rathena | master | 98 | 0 |
| RO／Hercules | [monkey1sai/Hercules](https://github.com/monkey1sai/Hercules) | HerculesWS/Hercules | stable | 17 | 120 |
| 天堂 1／L1J-en Classic | [monkey1sai/classic](https://github.com/monkey1sai/classic) | l1j-en/classic | master | 2 | 0 |
| 魔獸世界／AzerothCore | [monkey1sai/azerothcore-wotlk](https://github.com/monkey1sai/azerothcore-wotlk) | azerothcore/azerothcore-wotlk | master | 7 | 19 |
| 魔獸世界／TrinityCore | [monkey1sai/TrinityCore](https://github.com/monkey1sai/TrinityCore) | TrinityCore/TrinityCore | master | 4 | 150 |
| Ryzom Core | [monkey1sai/ryzomcore](https://github.com/monkey1sai/ryzomcore) | ryzom/ryzomcore | core4 | 211 | 44 |
| The Mana World／伺服器 | [monkey1sai/tmwa](https://github.com/monkey1sai/tmwa) | themanaworld/tmwa | master | 42 | 96 |
| The Mana World／Mana 客戶端 | [monkey1sai/mana](https://github.com/monkey1sai/mana) | mana/mana | master | 8 | 36 |
| Veloren（官方 GitHub 鏡像） | [monkey1sai/veloren](https://github.com/monkey1sai/veloren) | veloren/veloren | master | 132 | 22 |
| 天堂 2／L2J 登入伺服器（鏡像） | [monkey1sai/l2j-server-login](https://github.com/monkey1sai/l2j-server-login) | l2jserver/l2j-server-login | master | 1 | 22 |
| 天堂 2／L2J 遊戲伺服器（鏡像） | [monkey1sai/l2j-server-game](https://github.com/monkey1sai/l2j-server-game) | l2jserver/l2j-server-game | develop | 31 | 8 |
| 天堂 2／L2J Datapack（鏡像） | [monkey1sai/l2j-server-datapack](https://github.com/monkey1sai/l2j-server-datapack) | l2jserver/l2j-server-datapack | develop | 23 | 8 |

## 報告的驗證狀態與範圍

報告列為已驗證（VERIFIED）的項目：
- 12 個倉庫的擁有者與公開可見性符合預期，9 個 fork 的上游正確。
- 全部分支與標籤的名稱、SHA 都和建立前的來源快照一致，差異為 0。
- 預設分支與 SHA 和來源一致。
- L2J 保留 GPLv3 授權。
- 沒有 Git LFS、submodule 或 workflow 檔，也沒有啟用任何工作流程或排程。

報告註明的範圍與限制：
- 只複製原始碼與 Git 歷史。
- 沒有編譯、啟動或驗收任何遊戲。
- 沒有複製 issue、wiki、release 附件，也沒有下載 Ryzom 的外部素材。
- fork 和鏡像都不會自動同步上游。

報告本身的交付前獨立複核狀態是 `REVIEWER_CAPACITY / BLOCKED`，不計為通過。

## 美術開發怎麼用（INFERRED：使用前先到倉庫核對）

以下是依專案性質推論的用途，報告本身沒有驗證這些內容；引用前要在倉庫裡找到實際檔案，並記錄 commit。

- **RO 劍士的技能資料**：Provoke、Bash、Magnum Break、Endure 的名稱、效果語意與時間參數，先查 rAthena／Hercules 的技能資料與文件，再對照本 repo 需求的連段契約，不要自行杜撰。
- **3D 角色與動畫管線方法**：Ryzom Core（含引擎與工具）與 Veloren（程式化角色動畫）可參考骨架、動畫混合、程序式動作的做法。
- **天堂 1／2、魔獸世界伺服器專案**：以伺服器邏輯與資料為主，對美術主要是動作、技能、裝備清單和命名的參考。
- **The Mana World**：2D 專案，主要參考資料結構與授權處理方式。

## 使用規則

- 製作前先查本清單和 `library/index.json`，確認沒有現成可用的資料或方法，再決定自製。
- 這些是外部倉庫，預設唯讀。
  - 需要時 clone 到本 repo 以外的位置，記錄倉庫與 commit SHA。
  - 不在本 repo 內 clone，也不把外部程式碼或素材複製進本 repo。
  - 確實需要複製時，要逐項核對該倉庫的 LICENSE 與素材授權，並取得使用者同意。報告只確認了 L2J 是 GPLv3，其他倉庫的授權要自行核對。
- 參考資料只影響外觀與動作設計，不得改寫遊戲規則、命中範圍或碰撞（見 `AGENTS.md`）。
- 這份清單反映 2026-10-05 的報告內容；倉庫之後若有變動，以倉庫實際狀態為準。
