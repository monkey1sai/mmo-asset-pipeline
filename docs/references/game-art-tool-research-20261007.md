# 遊戲美術工具與資源研究：2026-10-07

本文件是選型與導入依據，不是工具已安裝／已連線／已驗收的報告。不以網站行銷圖保證實際輸出，不購買或下載未授權原始素材。只查主要維護者及官方文件；外部程式碼、sample 資產、模型權重沒有複製進本 repo。

## 值得採用的專業方法

**動作來源與播放系統分工。** Epic 的 Game Animation Sample 展示高品質動作資料、locomotion 與可操作除錯場景；distance matching 將動作進度與移動距離聯繫。對本 repo 的推論是：保留已完成的轉場與腳鎖定，另外提升來源動作、步幅／速度匹配和重定向品質，而不是只加平滑。這是方法借鑑，不是要本 repo 改用 Unreal 或複製 Epic 素材。

**rig 不只靠骨頭名稱對應。** Godot 官方 retarget 文件說明 rest transform／骨架比例等差異。對本 repo 的推論是：每個外部 motion 有自己的 source rig fingerprint，經 bone map／rest alignment／scale／root policy 處理後才 bake 到凍結 target。Rigify 類控制骨架／插件只是製作輔助，不應直接被當成 runtime 可交換契約；實際 Blender glTF 匯出能力依版本核對。

**製作與交付兩次檢查。** Blender 的 glTF 文件列出支援材質及動畫範圍；不是 DCC 裡能動，輸出就包含相同約束與效果。Khronos validator 驗結構，實際外觀與 target runtime 另驗。glTF Transform 的壓縮與貼圖處理適合合格後的衍生優化，不應在凍結角色上無條件改拓樸。

## 來源與導入決定

| 工具／來源 | 官方依據 | 本工作台導入方式 | 尚未證明的部分 |
|---|---|---|---|
| Adobe Mixamo | [官方 FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html)／[繁中](https://helpx.adobe.com/tw/creative-cloud/faq/mixamo-faq.html)：Adobe ID 可用，人形自動 rig、角色／動作可用於商業遊戲等專案 | 基本步態／跑步／互動動作候選；授權 UI 匯出，不虛構 API | 本帳戶可用性、target retarget、原始素材公開再散布權未證明，預設不匯入公開 repo |
| Meshy | [Rigging API](https://docs.meshy.ai/en/api/rigging)、[Animation API](https://docs.meshy.ai/en/api/animation)：現有模型綁定、動作工作流；輸入、方案與 action 欄位有限制 | 候選 auto-rig／animation provider，不替代既有角色 master | 方案／費用、當前模型／動作 ID、輸出品質與原始再散布權需 probe。文件列出舊模型退役日期，不能把舊 ID 長期寫死 |
| Tripo | [Rig](https://developers.tripo3d.com/en/models/rig)、[Animation](https://developers.tripo3d.com/en/models/animation)、[舊版 rig 文件限制](https://docs.tripo3d.ai/animation/rig-v2-0-20250506.html) | rig check／retarget 的替代路線，按實際版本及輸入模型選擇 | 不同文件世代支援類型有差異；重拓樸／拆件後不能假設既有 rig 和動畫保留；帳戶與授權未驗 |
| DeepMotion | [Animate 3D](https://www.deepmotion.com/animate-3d)、[Terms](https://www.deepmotion.com/terms-of-use)：影片動捕、足部處理與多格式輸出，API 存取需另外核對；條款限制 standalone raw data 再散布 | 自有影片的自訂動作候選，特別是現成庫找不到的動作 | 沒有上傳影片、開通 API 或花費點數；公開原始動作匯入被阻擋 |
| Blender | [官方 glTF 文件](https://docs.blender.org/manual/en/5.3/addons/scene_gltf2.html)；repo 記錄4.5.5 | 主要 DCC；新增獨立安全 session 的固定 beauty／clay GLB 預覽腳本 | 引用較新手冊不能證明4.5.5各API相容；本套件尚未實際執行 Blender |
| Rokoko Blender | [官方插件 repo](https://github.com/Rokoko/rokoko-studio-live-blender)：retarget與 bone mapping，程式 LGPL | 可選重定向工具；先探測已裝工具，不自動安裝 | 目前 Blender版本／插件相容性、特定 target 效果未測；插件授權不是來源動畫授權 |
| Poly Haven | [License](https://polyhaven.com/license)：素材 CC0；網站其他內容及 API 另有規範 | PBR、HDRI／模型的優先資源之一，已授權下載後用本機收據匯入 | 逐件需求適配、相依內容及來源核對；不爬站、不當作免費無限制 API |
| ambientCG | [License](https://docs.ambientcg.com/license/)：素材與預覽 CC0 | 材質與環境來源，逐件記錄原檔與版本 | 使用者本機是否已取得素材、實際色彩空間與尺度未驗 |
| Material Maker | [官網](https://www.materialmaker.org/)、[官方 repo](https://github.com/RodZill4/material-maker)：程序材質、3D painting；MIT但個別檔例外 | 參數化材質配方候選，不強制導入另一個服務 | 沒有安裝、執行或驗證 node graphs；外部節點／輸入仍分別核權 |
| Khronos glTF Validator | [官方 repo](https://github.com/KhronosGroup/glTF-Validator/)、[官方本機瀏覽器工具](https://github.khronos.org/glTF-Validator/) | 新增本機 Node wrapper，實際呼叫 `validateBytes` 並記錄版本與檔案SHA | 本次沒有安裝 npm validator 或對真實 GLB 執行官方驗證；依賴缺少測試確認回 not_run |
| glTF Transform | [官方文件](https://gltf-transform.dev/)：壓縮、貼圖處理、meshopt等 | 指定 runtime 下的交付優化；另存 derivative，做前後畫面與解碼驗證 | 未安裝、未壓縮模型，LOD/動畫精度不能預先保證 |
| Epic Game Animation Sample | [官方文件](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine)、[Distance Matching](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine) | 方法參考：自然動作來源、資料庫、可操作QA、步幅／移動距離一致 | 非完整動作系統移植；sample原始素材跨引擎／公開再散布權未核對，未複製 |
| Godot retarget 文件 | [官方文件](https://docs.godotengine.org/en/4.7/tutorials/assets_pipeline/retargeting_3d_skeletons.html) | 跨 rig 方法參考 | 不代表本次已測 Godot，也不是新增 mandatory engine |
| Hyper3D／Rodin | [官網](https://hyper3d.ai)、repo `docs/api-creation-workflow.md` 與既有能力表 | 保留原 API 創作路徑，不另造付費執行器 | 本輪未探測帳戶／adapter／月訂餘額，也未生成模型；官網能力不是本輪執行證據 |

## 與既有 MMORPG 開源倉庫清單的關係

保留 `mmorpg-github-sources.md`。rAthena、Hercules、L2J、AzerothCore 等伺服器／資料專案主要能參考語意、資料與命名，不能直接當成商用3D素材庫。Ryzom／Veloren 等的工具與動畫方法可研究，但原始碼授權不自動涵蓋所有外部素材。引用實作前記 exact commit 和個別 license；本次沒有複製這些外部專案的程式或素材。

## 採用順序與證據等級

先沿用工作台、Blender、Hyper3D及cv1 QA；補本機來源收據、固定比較和真正glTF validator入口。接著用目前角色的一段步態做來源／retarget實驗，再依需求擴展材質與模組道具。Meshy／Tripo／DeepMotion／Rokoko 是具體候選，不是「全部都要安裝」。

每項能力分 `documented`（文件宣稱）、`available`（此帳戶／版本可用）、`executed`（此資產真的產生輸出）、`accepted`（需求適用各關卡通過）。本套件研究資料不跨級。所有花費、插件安裝、外部儲存或Git寫入仍依原使用者範圍。
