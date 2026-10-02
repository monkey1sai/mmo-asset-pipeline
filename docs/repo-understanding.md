# 三個 repo 的需求與現況

本文件記錄 2026-10-02 對首批客戶 repo 的唯讀理解，以及既有候選清單的來源。EvoLoot 與 changshan-longdan 是通用美術工作台目前的兩個需求來源；核心不限定這兩款遊戲或 Unity。後續需求依 `art-workflow.md` 指定用途、製作路徑及交付範圍。

`catalog/assets.json` 的 39 筆是需求，包含 EvoLoot 17 筆、共用地牢套件 3 筆、changshan-longdan 19 筆。最後一筆是既有趙雲的重用登記，因此共有 38 筆新增候選，不代表已送出 38 次生成，不代表已下載或可用。多個同族候選可以透過材質、配件和同一模型衍生，不能為了用完點數而重複產製。

## 來源版本與檔案狀態

| repo／工作樹 | 本次來源 HEAD | 觀察到的狀態 | 可支持的結論 |
|---|---|---|---|
| `C:\Repos\mmo-asset-pipeline` | 初始化時沒有 HEAD | 僅有 `.git`，本次建立未追蹤的清單、工具與文件；尚無可作起點的 commit | 這是新的素材工廠，沒有既有生成、QA 或遊戲接入證據 |
| `C:\Repos\EvoLoot` | `718c6d38bc2de86458988c212472ce16cd418c5c` | `master`，13 個 tracked 修改，以及圖片、Jev、Godot 插件和新測試等未追蹤檔案 | 程式與文件顯示目前本機開發內容；dirty／未追蹤內容不能說成 HEAD 已提交的功能 |
| `C:\Repos\changshan-longdan` | `a42c9294c32ac8ff566bc019dc5465b9dc7ad1d9` | `main`，未追蹤 `%SystemDrive%/` 與 `.worktrees/` | 主工作區仍是 TypeScript／Three.js 程序模型遊戲 |
| `C:\Repos\changshan-longdan\.worktrees\e00-recoverable-baseline` | `af771bd2a1ca2d1968c3e46f1d2fe2608ebcbb3e` | `codex/e00-recoverable-baseline`，本次 Git 狀態乾淨 | 專用趙雲 GLB adapter 在這個工作樹，不等於主 `main` 已整合 |

清單 `sources[].head` 是 repo 或工作樹的基準識別，`path`／`line` 指向本次實際讀到的本機來源；若來源檔在 dirty／未追蹤集合，note 有註明。HEAD 不能單獨證明 dirty 檔案的內容。正式批次產製前應再次檢查來源 HEAD、相關檔案及既有模型，並把本次操作的輸入、雜湊與結果寫入 runs 證據。未做來源快照時，不能宣稱需求由一個不可變 commit 完整重現。

EvoLoot 的根 AGENTS.md 中 repo root 仍寫 `C:\Repos\active\ai-app`，本次以實際目錄與 source 為準，不修改另一個 repo 的指引。

## EvoLoot：活體武器與世界變化 RPG

VERIFIED：目前主產品是 Streamlit RPG，已有規則式戰鬥、武器進化、共享世界狀態、老鐵匠對話與修復；可選模型呼叫與 Jev 是開發中的 AI 相關能力，不能取代規則和資產驗收。入口是 `C:\Repos\EvoLoot\EvoLoot\app.py`。

遊戲現在的核心需求比泛用奇幻種族庫更明確：

- `EvoLoot\services\game_service.py:80` 明確建立 MVP 人類戰士；`domain\entities.py:18` 與 `:34` 定義九職業與八種族，但 enum 不等於每種都有可玩角色選擇、3D 模型與動畫。本次不因此擴大為全部種族／職業批量生成。
- `EvoLoot\domain\entities.py:519` 是基礎鐵劍；`EvoLoot\config.py:243` 定義 Neutral、Greedy、Bloodthirsty、Loyal、Chaotic 五人格。因此五把活體劍以共同握柄、長度與 pivot 製作不同刃形／配件／材質，直接支援已有玩法。
- `EvoLoot\data\monsters_seed.json` 定義普通、冰霜、暴走及王史萊姆，哥布林掠奪者、菁英哥布林、巫妖、傳說巨龍與鏡像獵手。這是敵人資料需求，不能說所有模型或 encounter 均已完成遊戲接入。`EvoLoot\api\realtime.py:168` 的本機 realtime 初始敵人實際是 Realtime Goblin。
- `EvoLoot\services\world_service.py:81` 依溫度、混亂與魔力切換環境；`:164` 起有潮濕石壁、寒冰、岩漿、落石與魔力粒子文字。地牢石壁、地板及拱門是由已有環境推導的模組需求，形式和尺寸仍屬本次提案。
- `EvoLoot\app.py:553` 與 `EvoLoot\services\npc_service.py:17` 已有老鐵匠對話／修復；老鐵匠是來源支持角色，鐵砧則是依用途推導的道具。

VERIFIED：Godot 主場景 `godot_client\scenes\BattleScene.tscn:11` 是 Node2D，MonsterDisplay 和 WeaponDisplay 都是 TextureRect，資源是 JPG。`godot_client\scripts\state_sync.gd:108` 依名稱把 boss 換成惡魔圖，其他敵人仍 fallback 為 slime 圖；`:114` 依進化階段／名稱選 neutral 或 greedy 圖。`EvoLoot\infrastructure\asset_manager.py:21` 也只回傳 JPG 路徑。新增 3D 模型不會自行出現在這個 2D 畫面。

Godot 已啟用未追蹤 RodinBridge 插件，插件有 glTF／Node3D helper；BattleScene 尚未使用這些 3D helper。本次沒有讀取 plugin settings 或憑證。資料庫、圖片管理器、模型生成服務和 3D runtime 是四個不同層，不能互相替代證據。

## changshan-longdan：三國戰場與大量敵軍

VERIFIED：主工作區透過 `src\game.ts:23` 的 PlayerModel、SoldierView、Dragon 和 buildCastle 建立程序／體素視覺，沒有通用 AssetPack／ModelSlot。美術意圖是風格化三國、英雄式比例，銀甲綠布長槍趙雲須保持遠距識別；Environment Bible 的村口、植被與少量 NPC 是未來規劃，不能當作現在城池 runtime。

`src\world\layout.ts:1` 集中渲染與碰撞公尺座標，Y 向上、南門在 +Z，INNER 為 56、城牆厚 6 m、高 9 m。六棟兵營的 footprint 深度有 13／14／15 m 變體，16 座火盆、兩處屋頂火、兩處地面殘骸都有集中來源；素材尺寸必須接回這些配置，不能直接重新塑造戰場碰撞。

`src\entities\enemies.ts:160` 與 `src\world\layout.ts:55` 支持 25 小隊、每隊 12 人，共 300 魏兵；類型包含槍兵、劍盾兵與隊長。`src\view\soldier-view.ts:165` 現有八類 InstancedMesh 共用材質並更新部位矩陣。人物生成的 A pose、貼圖或外觀不是現有部位實例化的替代品。

INFERRED：把 300 敵兵直接換成每隻 30,000 三角形的獨立蒙皮模型，會有 9,000,000 基礎三角形，還會失去現有實例化優勢。本次建議普通兵候選 4,000、隊長 5,500 三角形、1K 貼圖，並要求共享骨架／材質／LOD 方案；這是產製起點，不是 repo 原本性能承諾，也沒有取得實際 300 兵 runtime PASS。

城牆、門樓、四角塔、主殿、兵營、火盆、吊燈、箱子、殘骸與遠山已有 `src\world\castle.ts` 程序視覺，適合先保存成可重用模板。完整／焦黑兵營應重用基礎幾何，動態火焰與發光部分留給引擎；`src\fx\dragon.ts:36` 的青龍仍沿程序分段身體運動，因此清單只登記可接合的龍頭，不能把僵硬完整巨龍視為可直接替換。

## 既有趙雲：優先重用，禁止重複花點

VERIFIED：e00 工作樹的 `src\view\zhaoyun-adapter.ts:5` 與 ZhaoYunSkin 載入 `models/zhaoyun.glb`，驗證 SM_ZhaoYun、SM_ZhaoYunSpear 與 21 個特定骨名稱，並以既有程序招式／握點驅動。這是針對一份特定模型的 adapter，不能當成所有 Hyper3D 角色的自動綁骨能力。

`docs\art\zhaoyun-integration.md:11` 文件記錄該 GLB 是 29,569 三角形、3,706,788 bytes、21 骨、三張 2048×2048 內嵌貼圖、無時間獨立動畫 clip、僅 LOD0。本次已查 source 與文件，沒有重驗 GLB 二進位、動畫或歷史瀏覽器證據。因此 `cl-zhaoyun-reuse` 只表示重用優先權，不能寫成已通過本次技術／runtime／Unity 驗收。

## Unity 與本次驗證界線

VERIFIED：本次唯讀探索範圍沒有找到兩個主 repo 的 Unity ProjectSettings、Unity 場景或 C# 匯入流程。Unity 是使用者的未來方向；本 repo 先製作可追溯 GLB／PBR master 與需求規格，Unity importer、材料、rig、動畫、Collider、prefab 必須後續在實際專案驗證。GLB 下載成功不構成 Unity 可用證據。

本次沒有啟動兩個遊戲、執行它們的測試或瀏覽器驗收，避免讀取流程寫入現有世界狀態。EvoLoot `docs\current_task.md` 的 680 tests／95.26% coverage 與 Godot 截圖，e00 的 103 tests／Chrome／性能記錄，都屬歷史文件內容，不列為本次通過。

後續依需求核對來源及既有模型，選重用、修改、生成或拆件，完成必要後製與驗收。獨立資產不要求遊戲接入；指定目標環境才實測該環境。offline GLB inventory 只支持報告列出的局部資料，不能證明 UV、法線、尺寸、pivot 或完整技術驗收。此文件不授權改動另外兩個 repo、不建立月排程、不授權加購／升級或使用普通點數。
