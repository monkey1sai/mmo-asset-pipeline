# RO 劍士：獨立手部與配裝新階段

使用者已授權方向1，以產製成本及失敗證據改進美術工程師的策略與方法。
目前是**已完成準備及真實baseline；新手套未生成；完整角色仍NO-SHIP**。
r005原階段已關閉，全部失敗、14,607.710521秒、三次修訂與1.0點服務回報保留。
本階段沒有stage、commit或push。

## 可檢查成果

- [新右手手套設計圖](../../../assets/raw/ro-swordsman-combo/design-v006/right-glove-open.png)：
  五指分離、中性掌面、厚實拇指根及短腕口；built-in image_gen，未以程式改像素。
- [設計brief與完整prompt](design-brief.md)、[完整需求](../../../requests/ro-swordsman-combo-r006.json)：
  保留60,000tri、300幀／60fps、可編輯rig、分離可關閉VFX及BLEND／GLB要求。
- [真實中性baseline](baseline/three-quarter.png)、[右手握持側面](baseline/grip-R/side.png)、
  [左手握持掌側](baseline/grip-L/palm.png)。
- [baseline BLEND](../../../assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.blend)
  及[GLB](../../../assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.glb)。
  是失敗基準，不能當交付包。

## VERIFIED：本次實體基準

使用Blender4.5.5LTS獨立背景程序，沒有呼叫`read_factory_settings`或改全域偏好。
48骨、58,868tri，修正指軸後做五個完整固定視角與左右張掌、小屈指、单手握持四近照，
共29張PNG。來源幾何、UV及權重逐項回讀相同；來源master的SHA不變。

角色高度實測1.7399998903m，腳底minZ0；rig及root位於原點。
全部網格綁到同一rig，最多4影響、權重正規化且無invalid。
GLB結構實查一個skin／48joints／0animation／6embedded images。
這些是部分靜態證據；沒有新GLB匯入播放或完整動畫驗收。
匯出有sampler警告，未假定無害：`More than one shader node tex image used for a texture`。

右手固定指墊中，最深樣本穿入約7.05mm；左拇指最近距柄約23.68mm。
實際近照仍見掌根摺疊、指墊接觸不足及腕甲穿插。
兩條射線在這些樣本無分歧，但不代表完整三角面交叉已驗證。

[baseline.json](baseline/baseline.json)、[技術量測](baseline/technical-measurements.json)、
[評分／缺口](baseline/review.json)、[品質帳](quality-ledger.json)及[比較結果](comparison-baseline.json)
保存實際方法。比較為`revise_current_best`、候選0次、品質目標false；不表示成品可交付。
未做的runtime項目明列`runtime_execution_status:not_run`，其缺必要內容的驗收失敗
不被描述成已執行的播放或匯入失敗。

## 已固定的下一輪方法

[局部關卡](hand-gate-contract.json)及[雜湊綁定](baseline-binding.json)：
姿勢／相機、語義指墊遮罩、2mm接觸、1mm深穿入、真正面交叉、腕口／掌根變形與UV。
只有實際右手用途關卡通過才擴展左手、全角色及完整連段；灰模只是額外診斷。

[面數量測](hand-budget-scout.json)：規劃切除右492、左537tri後留57,839tri；
預留256tri腕縫後，每手最多952tri。尚未切除任何面。
新手套實際tri下載後再測；若必要，先另存硬肩甲／護臂的減面版本並驗輪廓、材質及配裝。
不能降低60,000整件上限，也不能把API的1000 target當實測。
[獨立覆核](planning-review.md)指出以上两项修正；來源可rig與可鏡射仍待實物。

## API與待完成條件

新operation `ro-hand-source-20261003-001`：
[計畫](generation-prepared.json)、[API spec](api-spec-hand.json)及
[不扣點預檢](api-preflight.json)已保存。認證成功，當時餘額228；分項未回傳。
離線估算本筆0.5點；未付費提交、未下載新3D來源，新增API扣點為0。
既有按需月訂／普通點數授權沿用，沒有新API點數上限、加購或升級。

待人類精確授權新增／更新：
`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-hand-source-20261003-001.dpapi`。
檔案目前不存在，只供此task加密恢復查詢，不含主API密鑰；保留舊檔與全域設定。
沿用使用者「repo外檔案列出確切變更再授權」要求，沒有把點數範圍重問一次。

下一步取得上述檔權後，核對仍無pending／unknown、輸入／需求／provider雜湊及即時餘額，
只提交這個prepared operation一次；後續查同一task，完成後下載到新raw目錄。
新來源再進Blender形體／面流／骨位／權重／握持與配装預檢。

本階段時鐘在3D baseline前登記；8修訂、每輪6h、總48h為本機實驗規劃。
先前image工具19.6秒另存；更早規劃總wall time未量測，不宣稱生命週期完整總時間。
前階段成本與時鐘不被新phase清空。

[本次準備驗證](preparation-verification.json)：116 tests／2.054s通過、舊39件清單結構有效；
29基準PNG、模型／來源／固定契約雜湊與6個新腳本語法核對通過，沒有新增Hyper3D付費生成。
[工作流學習紀錄](workflow-learning.json)分開保存已驗規則、待實測假設與未量測成本。
已更新`docs/art-workflow.md`及本repo的art-engineer skill，但不能宣稱新手套或最佳工作流已驗收。

目前沒有本任務API、Blender、reviewer或其他背景工作繼續執行。
