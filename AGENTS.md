# 需求驅動的 3D 美術工程工作台

- 核心流程依 `docs/art-workflow.md`：理解需求、制定設計、選擇重用／修改／生成／拆件、製作與後製、依需求驗收、交付歸檔。需求決定必要步驟。
- 本 repo 的美術資產需求、修訂、驗收與歸檔使用 `.agents/skills/art-engineer/SKILL.md`（`$art-engineer`）；既有 workflow 與工具仍為規格來源。
- 素材展示影片、技能演示剪輯另依 `docs/video-skills.md`：`$video-shotcraft` 處理分鏡／Remotion 動效，`$video-use` 處理既有錄影剪輯。技能以固定 commit 的 project-local submodule 安裝；先確認初始化與相依工具，不自動追最新。影片不取代模型、骨架、動作或 runtime 驗收；API／音樂／素材用途依當次授權，密鑰只使用既有憑證提供者，不要求貼進聊天。
- 新製作及品質修訂依 `docs/art-quality-loop.md` 凍結品質標竿與評估條件，先做 baseline，再以有界實驗比較；任一維度退步不得用其他高分抵銷。有 `quality` 的需求必須由 `assess` 核對實驗紀錄與已評估交付內容；不把分數宣稱為自動美術 PASS 或「頂尖」保證。
- 只在本 repo 維護需求、工程師資產、產製工具與證據。`projects/` 是選用客戶規格；EvoLoot、changshan-longdan 是首批來源，不能寫死在核心。其他 repo 預設唯讀；遊戲接入、Unity、push、PR、部署和排程依使用者具體範圍。
- 每次製作先查 `library/index.json`、需求、來源版本與現有 master。重新生成取決於需求差距和修訂成本；剩餘點數不能取代用途。遊戲美術不得自行改寫規則、命中範圍或碰撞。
- 美術設計與製作前，也查 `docs/references/mmorpg-github-sources.md`（使用者指定的 MMORPG 開源倉庫參考清單）可重用的資料、方法與命名，避免重造輪子；外部倉庫唯讀引用並記錄 commit，逐項核對授權並經使用者同意後才可複製。
- 自然語言先形成 `requests/` 草稿。低風險預設寫入 assumptions；真正影響用途、功能或交付的缺項才詢問。`intake` 保留原文，不宣稱已自動理解完整規格。
- 骨架、動畫、LOD、拆件與目標環境驗收由需求明確指定。獨立資產不強制 Unity；指定目標環境才驗該環境。美術、技術、目標環境、交付狀態分開保存。
- `assess` 只核對證據格式、需求雜湊及本機檔案雜湊。`eligible_for_delivery_review` 不是自動交付通過，不能取代美術判斷、DCC 實測或目標 runtime。
- 原始 master、後製與交付包皆隨 repo。依 `docs/asset-storage.md` 使用 Git／Git LFS，禁止忽略整個 assets 或 deliveries；雲端網址不能代替本機交付檔。保留來源、索引、版本、相依檔及使用說明。
- LFS 指標、本機 LFS 物件、遠端同步與重新 clone 還原是不同證據。`git add`、commit 與 push 依當次使用者具體授權；先核對遠端可見性及既有歷史，不擅自改可見性、加購配額、安裝 hook 或修改全域 Git 設定。
- Hyper3D API 是美術工程師在需求整理後的創作工具；生成路徑優先使用當下可用 API，依 `docs/api-creation-workflow.md` 完成輸入設計、提交、追蹤、下載與後製。網站只用於額度證據或有明確理由的備援，不能把工具／額度限制說成只能網站生成。
- Hyper3D 只使用使用者明確授權的月訂額度；普通點數、加購、升級不在預設範圍。API 總餘額不能替代月訂／普通分項。金額與點數以即時服務回傳為準。
- 密鑰使用既有受支援的憑證提供者。禁止在 repo、命令列、log、聊天或 Git 保存密鑰、subscription_key、cookies、signed URL。
- 付費提交前保存唯一 operation ID 與需求。pending／unknown 不自動重送；先查服務狀態。未知／缺少狀態使離線計畫停止；failed／cancelled 保留既有操作，由新證據決定新修訂。每筆扣點、下載及 QA 分別記錄。
- `generated`、`downloaded`、`technical_checked`、`art_accepted`、`technical_accepted`、`delivered`、目標遊戲 `game_ready` 是不同狀態。只做 inventory 不得宣稱完整技術通過；未完成指定骨架／動畫／LOD／引擎驗收不得宣稱該目標可用。
- 使用 `python -B -m unittest discover -s tests -v` 驗證工具；`python -B scripts/pipeline.py validate` 驗證既有清單。不得把其他 repo 的歷史測試當本次證據。
- 一個協調者負責寫入；獨立子任務預設唯讀。尚無 HEAD 時先保留可審查的變更與暫存，核對遠端歷史；只有當次明確授權才建立提交，不修改 Git 權限。保留既有 Unity 專用工具與測試，一般資產需求使用 `$art-engineer`。

<!-- art-production-upgrade-v1 -->
## 資源支援的美術製作增補

- 新需求／品質修訂另讀 `docs/art-production-upgrade.md` 與 `docs/references/game-art-tool-research-20261007.md`。保留既有核心規格、品質門檻、凍結需求與授權，不用此增補覆寫它們。
- 工具／來源清單在 `tools/art-sources/catalog.json`：文件能力、當前可用、實際執行、驗收通過分開記錄。先查本庫，再比較外部來源、修改與生成；不把每件素材強制套用同一風格、遊戲、引擎或整套工具。
- 角色動作先比較已授權動作來源與重定向，不只調平滑曲線。保留 target rig／rest pose／拓樸／權重及既有 cv1 runtime QA；重新綁骨不是預設解法。靜態道具不強制動畫。
- 本 repo 公開。商業專案使用權與原始素材公開再散布權分開審查；未知即不匯入、不 commit/push，不偷偷改可見性或繞過原資產保存規範。
- `scripts/art_sources.py` 只做本機來源檢查及明確 `--apply` 的新版本複製，不驗美術或動作；`scripts/blender_art_preview.py` 需獨立安全 Blender session 與凍結預覽協定；`tools/art-validation/validate-glb.mjs` 需真正 Khronos validator。三者都不能替代既有 `assess`、目標 runtime、美術或交付審查。

<!-- git-management-v1 -->
## Git 管理原則

- 具體流程依 [Git 管理與工程 checkpoint](docs/git-workflow.md)。預設 feature branch；dirty、平行或品質實驗使用隔離 worktree，一個 commit 只處理一個主題。
- commit 前核對 status、diff、相關測試、staged diff 與清單；只 stage 本任務檔案及區塊。保留他人 staged／unstaged 修改，混入無關內容時先隔離本任務，不擅自移除或提交他人修改。
- 已驗工作先形成可回復 checkpoint，再做高風險實驗。只在具體目的地／branch 的人類授權內 commit／push，push 前重查範圍與必要 review，push 後確認同一 SHA 的 CI；feature push、CI 綠燈不授權 merge。
- PASS、FAIL、NOT_RUN 分開記錄；已執行但結果不可核實則 UNVERIFIED。依賴缺少、受阻或 skipped 不算 PASS，commit／push 不代表 runtime 通過。
- 實驗保留 baseline、candidate、凍結條件、失敗與 evidence；安全回退遵循授權。禁止未授權 reset --hard、clean -fd、force push、證據刪除、權限／protection 修改。main/master 保持可使用、可驗證、可回復。
