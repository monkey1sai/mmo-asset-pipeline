# 資源支援的高品質遊戲美術製作

研究／套件日期：2026-10-07。依據 `monkey1sai/mmo-asset-pipeline` 主線 `08c454e6c6e7566f7a7625953773b6eb18693f5c`。

本增補的目標是增加美術工程師的製作能力，不是再以文件分數證明「頂級」。保留 `AGENTS.md`、`docs/art-workflow.md`、`docs/art-quality-loop.md`、既有授權、品質契約與工具；若有衝突，先停止相衝突的新步驟，不能降低既有門檻。新品使用本增補；舊凍結需求不直接改 schema、digest 或已核准骨架。

## 1. 現況與真正要補的能力

目前不是從零開始。PR #7 已合併角色片段、Python／JavaScript 轉場權重、腳鎖定、Blender 轉場檢查和 `tools/runtime-qa/three/p4.html`。PR 記錄的轉場矩陣是 **164 組中 115 組通過**；皺褶 collapse 47 組與 1.5 倍速腿長極限 5 組是失敗分類，不能直接相加當成互斥案例數。使用者接受美術審查，不表示原數值門檻全部通過。P3 剩餘連段與 P5 凍結／holdout 不在該 PR 的完成範圍。這些是上游記錄，並非本套件在 Blender 重跑的結果。

已有的 `tools/capabilities.json` 只有 Hyper3D、Blender、GLB inventory 與 workbench 的能力描述。本次新增研究目錄與入口，不把它改成「所有雲端工具已連上」。

要補的是四件事：高品質參考與來源選擇、可重用製作配方、固定條件實物比較，以及動畫觀感／材質／目標效能的分開驗收。腳不滑、轉場連續、runtime 數值吻合，仍不足以證明人物有重量感或自然步態。

## 2. 每張委託先作三個決定

**品質目標**：以目前需求的用途、風格、最近觀看距離與實際顯示尺寸，選具體輪廓、材質和動態標竿。英雄近景、群眾角色、背景道具不能共用一組「AAA 面數」。4K／高面數不是品質證明。先從既有 reference 與品質契約接續，不重定義使用者已接受的美術方向。

**生產路線**：先查 `library/index.json` 與現有 master，再比較現成授權來源、修改、生成或拆件。角色的「模型來源」與「動作來源」分開決定；好看的模型不代表有好用的 walk clip。靜態道具不強制 rig；互動道具先決定 pivot、拆件與全活動範圍；模組場景先定尺度／接縫／材質家族。

**接受條件**：美術、技術、動作、效能、授權、交付各自列門檻，不能互相抵銷。未定義目標引擎時保持獨立資產交付；本工作台的 Three.js QA 是測試載具，不是強迫所有客戶使用 Three.js。

## 3. 工具路由：少量核心、按需求外掛

| 製作需求 | 優先路線 | 替代／研究路線 | 禁止誤判 |
|---|---|---|---|
| 模型與局部修整 | 既有 master → Blender；缺形體才沿現有 Hyper3D 流程生成 | Meshy／Tripo 按需求試驗 | 生成成功不等於面流、拓樸或裝配合格 |
| 材質與燈光參考 | Poly Haven／ambientCG 的適用 CC0 素材；Blender lookdev | Material Maker 程序材質 | 寫實掃描材質不可無差別套到風格化模型 |
| 人形基本動作 | 自有合法 clip；評估 Mixamo 作比較來源 | Meshy／Tripo 動作工具 | 不假裝 Mixamo 有已接通的官方自動化 API |
| 自訂動作 | 自有關鍵幀或已授權動捕 | DeepMotion 自有影片動捕 | 有商用權不等於原始動作可放公開 repo |
| 重定向 | 對應骨架、rest pose、比例與骨軸，沿既有目標 rig bake | 核准後探測 Rokoko Blender 插件 | 骨頭同名不表示可直接混用；不任意換 target rig |
| 固定靜態預覽 | 本增補 Blender beauty／clay 擷取腳本 | 需求指定更完整的 wireframe／UV／lookdev scene | 圖片只是觀察材料，不自動美術 PASS |
| GLB 結構 | 真正 Khronos glTF Validator | 官方本機瀏覽器工具 | 自製 inventory 不是完整 validator |
| 最終優化 | 需求明定後，以 glTF Transform 等工具另產衍生版 | 目標引擎適用壓縮／LOD | 不破壞凍結 rig／topology；不能省掉解碼器與畫面驗證 |

各來源的官方文件、限制、可用性分類，見 `tools/art-sources/catalog.json` 與研究文件。`not_probed_this_run` 是本次沒有連線探測，不否認舊 repo 曾有特定操作成功。

## 4. 動作自然度：先用現有角色建立 A／B 實驗

第一個建議試作是既有角色的走路品質，不是換新角色或重做整套動畫框架。沿用已接受的風格、同一個 master、固定 target skeleton、rest pose、拓樸及權重。

A 組保留目前最佳 walk clip 與已知缺陷；B 組使用一段權利明確的高品質來源動作，經 retarget 成相同 target rig。來源可為已持有動作、人工修好的關鍵幀、可合法採用的動捕或服務輸出。沒有明確來源權利時，先做方法比較與現有 clip 修訂，不偷渡原始素材進公開 repo。

流程：

1. 先記 source rig 指紋、target rig／rest／權重／geometry 雜湊、單位與骨軸。把 motion/root motion policy 明確寫成 in-place 或 root-motion；來源 clip 不直接覆蓋 accepted target。
2. retarget 在隔離副本進行。修正骨架朝向、骨盆高度、腳底位置、手腳比例及必要 bone map；調整權重或 geometry 若超出凍結契約，停止並另開明確修訂，不偷偷改掉基準。
3. 檢查來源步幅、週期與遊戲移動速度是否相配。不能把所有速度都靠同一段動畫強行加速；目前 1.5x 已知腿長問題不能因觀感改善就抹掉。
4. 人工／視覺比較骨盆承重轉移、左右腳交替支撐、腳尖／腳跟落地、軀幹與手臂的相位、起步停步和方向切換。先有合理的來源動作，再用 IK、腳鎖與轉場處理接觸和銜接；不是反過來以平滑掩蓋僵硬來源。
5. bake 完成後重新匯出、重匯入 GLB，沿既有 cv1 clip／transition／foot-lock／runtime 檢查。記錄可支援的速度範圍，需求中尚未支援的狀態填 not_run，不自行添加並宣稱通過。
6. 用相同相機、角色尺度、地面、燈光、速度與時間點保留 A／B 正常播放、慢速及接觸特寫。已有品質契約仍逐維度比較；不得改成單一總分抵銷退步。影片是補充材料；依目前 `assess` 能接受的副檔名，保留 PNG 和 JSON／Markdown 的正式證據，不能假裝 MP4 已經過其規則驗證。

對已凍結的品質迴圈，不追加未授權 trial 或清空舊失敗／時鐘。P5 holdout 使用未參與調參的動作或情境，但必須先按原需求凍結並取得該階段範圍，不能把訓練集 A／B 重播當 holdout。

宣告界線：**重定向成功 ≠ 動作自然；動作自然 ≠ 無穿插；DCC 通過 ≠ runtime 通過。**参考 Epic Game Animation Sample 的動作來源／可操作除錯方法，不要求轉用 Unreal，也不複製未核對授權的樣本二進位。

## 5. 材質、道具與模組場景的可重用配方

模型先修輪廓、比例、結構和可見接縫，再處理 UV、烘焙與材質。把金屬、皮革、布、木的表面差異做在材質與細節尺度，不只做顏色差異；依所用 glTF／Blender 版本核對貼圖色彩空間與通道。每份來源記真實尺度、貼圖尺寸、使用通道、normal 方向、UV／texel density 設定及適用觀看距離；這些是規格或量測，不能混在一起。

可重用單位是「有來源與參數的材質配方、模組組裝契約、可動部件、骨架／動作映射」，不只是 GLB 檔案。Material Maker 等工具可作參數化材質候選；此套件沒有安裝它，也沒有產生已驗證的 node graph。高低模烘焙、重拓樸及 LOD 依需求進行，不把 remesh 之後的角色當作仍沿用相同 rig 的安全小修。

固定照明下比較 beauty 與 clay：clay 看輪廓／比例／結構，beauty 看材質層次和閱讀性；再回到最終觀看距離與實際引擎檢查。不要把燈光變暗、改相機或換視角作為「模型改善」證據。縮圖下看不清的微細節不是先做的重點。

## 6. 新增工具的實際使用與界線

### 來源收據與安全匯入

先以既有 `workbench.py validate/plan` 整理需求。來源收據模板是 **未審查且不可匯入** 的草稿；必須填實際 request canonical SHA、逐檔 bytes/SHA、來源 URL／版本、權利審查證據與動作 metadata。request digest 沿 `scripts/identity.py` 計算，不用 JSON 原文 bytes 代替。

```powershell
python -B scripts/art_sources.py catalog --kind motion
python -B scripts/art_sources.py check --request requests/REQUEST.json --receipt requests/source-receipts/SOURCE.json --source-root AUTHORIZED_LOCAL_DIRECTORY
python -B scripts/art_sources.py import-local --request requests/REQUEST.json --receipt requests/source-receipts/SOURCE.json --source-root AUTHORIZED_LOCAL_DIRECTORY
```

前兩條唯讀；第三條預設也是 dry-run。**只有明確追加 `--apply` 才寫入新的 `assets/raw/<id>/<version>/`**，不覆寫已有版本、不改 library/index、不碰 Git／憑證／付費 API。程式只複製收據列出的檔案，不下載或掃描整個磁碟。收據在 `requests/source-receipts/` 或 `runs/evidence/`；權利說明證據在 `runs/evidence/`。

成功狀態只是 `imported_unverified`：雜湊確認的是檔案身分，不會自動證明權利宣告、模型有效、動作內容或相依檔完整。GLTF/OBJ 等引用檔仍須另查；本機安全來源也不代表可以自動執行裡面的 Blender script。

### 固定 Blender 預覽

將 `templates/art-preview-protocol.json` 複製到需求範圍，按 baseline 確認相機中心／尺度／視角與 Blender 版本後凍結。預設數字只是可調草稿，不是所有角色的高品質標準。相機以 **Blender Z-up 公尺座標** 記錄；**不按每個候選的 bounding box 自動重新構圖**。更改協定就必須建立新比較基準。

```powershell
blender --background --factory-startup --disable-autoexec --python scripts/blender_art_preview.py -- --asset assets/processed/ASSET/VERSION/model.glb --request requests/REQUEST.json --protocol requests/PREVIEW.json --out runs/qa/REQUEST/preview-v001
```

這是在獨立安全背景 session 操作，不附著到使用者正在編輯的 Blender，不開 `.blend`、不另存 master。輸出 beauty／clay 多視角 PNG、來源／協定／腳本 SHA、局部 mesh inventory。只支援嵌入資源的 GLB；外部 URI、未審查 extension、版本不符或已存在輸出資料夾會停止。貼圖壓縮等 extension 另走核准的匯入路徑，不為方便關閉檢查。

本次只有協定、路徑和 GLB 前置檢查測試；**Blender 4.5.5 中的實際匯入、材質、燈光、渲染相容性未執行**。首次真實 smoke test 前不能稱此 adapter 已驗。此腳本不拍動畫、不產生 wireframe／UV 審查、不量測變形或效能，這些沿既有工具與委託補齊。

### 官方 GLB 結構驗證

```powershell
node tools/art-validation/validate-glb.mjs --asset assets/processed/ASSET/VERSION/model.glb
```

wrapper 只呼叫真正本機 `gltf-validator`，沒有自己冒充官方驗證演算法。無該套件時回 `not_run`／exit 3，不下載、不安裝、不報通過。已有依賴時記錄 validator version、檔案 SHA、issues 統計與代碼；外部資源不讀取。需完整診斷時，用官方本機瀏覽器驗證器對同一 SHA 的檔案查看，確認不誤傳私有素材。

依賴安裝不在本套件自動範圍。需要時先核對 npm 套件官方來源及明確版本，由已授權本機代理在 `tools/art-validation/` 的專用 package 範圍新增 lockfile，禁止全域安裝或改動既有 Three.js package。exit 0 最多代表沒有結構 errors，warnings 仍須審查；不等於美術、rig、動畫或 game_ready。

## 7. 公開 repo 的素材授權關卡

分開記錄工具程式、模型／動作、輸入圖片／影片、輸出、素材原始檔與最終遊戲的權利。商用與公開原始再散布是兩個判斷。尤其 Mixamo FAQ 的遊戲商用說明不是本 repo 原始檔再散布證據；DeepMotion 條款對 standalone raw data 有限制。兩者在本增補匯入器預設阻擋。

Poly Haven 的 CC0 不自動涵蓋網站預覽／文字／logo，API 另有條款；ambientCG 依其官方授權頁核對。只記錄來源不等於真實授權已審查；receipt 的 approved 是對已完成審查的紀錄，不可為讓測試綠燈自行填寫。

權利衝突時停止該來源的匯入。不得擅自改公開性、忽略整個 assets、改用秘密 storage、把合法使用限制藏在 gitignore，或以修改／retarget 名義洗掉來源限制。新的 private-asset delivery 路線需要使用者另行決定；本次沒有建立。

## 8. 本機驗收與停止條件

先跑本套件新增 tests，再跑 repo 原有完整 `python -B -m unittest discover -s tests -v` 和 `python -B scripts/pipeline.py validate`。本套件的離線 56 個 component tests 不包含原 repo 的183項歷史測試；套用後以實際總數為準，不能把兩個數字直接相加當作整體執行成功。

之後用一份具體、已授權的小模型做 Blender preview + 官方 GLB validator smoke test；沿用当前角色做來源／retarget A／B 和既有 runtime QA；最後才考慮可重用材質與道具小套件。沒有真實模型、可用 DCC、明確授權、有效來源或剩餘修訂預算時，標記 blocked/not_run 並列出具體缺口，不宣稱完成頂級素材。

來源：[PR #7](https://github.com/monkey1sai/mmo-asset-pipeline/pull/7)、[凍結版本 AGENTS](https://github.com/monkey1sai/mmo-asset-pipeline/blob/08c454e6c6e7566f7a7625953773b6eb18693f5c/AGENTS.md)。外部方法的來源逐項列在研究文件。
