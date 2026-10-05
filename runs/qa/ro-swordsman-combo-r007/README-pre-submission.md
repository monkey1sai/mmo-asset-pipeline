# RO 劍士 r007：掌腕來源先驗與貼身配裝

**已完成新方法的設計、量測、實體失敗基準與非扣點 API 預檢；新來源 prepared_not_submitted。**
完整角色仍 NO-SHIP，候選修訂使用0／4；尚未生成新模型，新增Hyper3D扣點為0。
API按需月訂／普通點數授權沿用；待精確新增恢復檔權限，沒有重問點數或另設API額度上限。
commit／push仍held，沒有staging；目前沒有API、Blender或reviewer背景工作繼續執行。

## 本次實物與設計

- [新掌面圖](../../../assets/raw/ro-swordsman-combo/design-v007/right-hand-palm.png)／
  [同右手背面圖](../../../assets/raw/ro-swordsman-combo/design-v007/right-hand-back.png)：
  built-in image_gen製作，無程式像素修改。取消空手套內襯與翻邊，保留棕皮、五指與貼身短前臂。
- [裝配量測](assembly-measurements.json)：前臂235.890mm；護腕在腕後60..120mm的
  最小第一射線表面命中約31..33mm。這不是整圈自由空間、可見性或動作淨空PASS。
- [新需求](../../../requests/ro-swordsman-combo-r007.json)、[原API計畫](generation-prepared.json)、
  [目前局部契約v2](hand-gate-contract-v2.json)、[原契約與澄清保存](contract-clarification.json)、
  [獨立準備覆核](independent-preparation-review.json)。
- [真正完整基準圖](baseline/three-quarter.png)、[完全握持近照](baseline/frame-061/side.png)、
  [baseline BLEND](../../../assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend)、
  [baseline GLB](../../../assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.glb)。
  這些是舊v008失敗標本的byte-identical複本，不是新候選或已接受master。

## 新方法與先驗順序

1. 來源設計改為實際戴在手上的外表面，具有掌根／拇指對掌體積，腕區貼身，短前臂覆蓋接合。
2. 下載後先看真正3D解剖、五指／指蹼、內層與封底、關節區面流、腕部截面及中性自交。
3. API請求native OBJ／Quad／target1200，保存原生面與材質依賴證據；Quad參數不自動放行動畫用途。
4. 再驗骨位、各關節實際方向與權重；來源需要大幅重建時停止直接綁定，依原創圖重新判斷來源，
   必要重拓樸明列為substantial production，不說成微調。
5. 固定語義指墊與全部實際baked frames；張掌／接近階段不必接觸，但仍不得穿過武器。
   持劍區間要同時滿足五指接觸、無深穿入、面交叉、自交診斷與實際形體／材質／腕口驗收。
6. 護腕保持獨立剛性骨變換，保護外表面；core重複衣甲與內部配裝另量測，不用腕管膨脹掩蓋。
   右手整體局部關卡通過才擴展左手、壓力姿勢、完整連段、VFX與新GLB回讀。

185mm手長、75mm掌寬、50x40mm腕截面、80mm短前臂與55x55mm近端是設計目標，
不是新3D來源的實測。兩圖的前臂有額外長度，作為待裁切的來源餘量；不能把封底當腕縫。
正背方向、指長次序與皮裝相容；2D圖不能證明微屈bind、對掌樞紐或單層拓樸成立。
另存[完整掌面prompt](image-prompts.json)、[背面prompt](image-back-prompt.json)與未回傳的圖片金額。

## VERIFIED：真實基準與必要範圍更正

Blender4.5.5LTS，factory-startup／disable-autoexec；沒有呼叫factory reset或改全域偏好。
完整角色與劍57,039tri、53骨、max4influences／invalid0；core高1.739999903m、腳底約0。
GLB實際有1skin／1animation／161channels／11images，動畫只是61幀局部握持。
本次25張PNG、五個完整視角與五個姿勢的四近照已保存。

自交直接使用同次evaluated頂點與loop triangles，POINT original_id驗證順序。
相鄰關係依固定rest點身分；沒有posed焊接／重新三角化。
測法仍排除相切／共平面、部分鄰面折疊，不能把零值視為完全無自交。
腕管新對數0／0／18／290／137相對舊方法不同，明列為測法改變，未修改幾何就不宣稱改善。

| baked frame | 最深劍穿入mm | 橫向交叉對 |
| --- | ---: | ---: |
| 1 | 7.185 | 94 |
| 16 | 5.430 | 65 |
| 31 | 3.409 | 53 |
| 46 | 1.340 | 20 |
| 61 | 0 | 0 |

進一步實測[61幀＋60半幀](baseline/baked-interval.json)，共121個樣本，118個有劍交叉，
最大穿入7.345mm；整段局部原型未通過。只有frame61的五指surface subset通過，
同幀近照仍有掌根折疊與腕部鼓包。離散樣本也不是數學上的連續碰撞自由證明。
[r006追加範圍更正](../ro-swordsman-combo-r006/v008-baked-clip-scope-correction.json)
保留舊模型、閉合帳、成本與NO-SHIP／stop_budget；沒有把方法更正當作模型改善。

[baseline綁定v2](baseline-binding-v2.json)、[品質帳](quality-ledger.json)、
[目前比較](comparison-baseline-v2.json)、[需求證據核對](assessment-preparation.json)
為revise_current_best／not_ready，品質目標false。完全技能與材質等價的新GLB回讀未做。

## API、成本與恢復條件

operation：ro-hand-structure-20261003-001。兩張PNG、Gen-2.5-High、Quad、nativeOBJ、
target1200、PBR high2K；離線估算0.5點，實際扣點以服務回傳consumed為準。
[非扣點預檢](api-preflight.json) authenticated=true，當時總餘額227.5；分項未回傳，
這不是即時餘額聲明。新來源未提交，沒有新服務耗用或下載；nativeOBJ此任務runtime尚未驗證。
官方[Gen-2.5規格](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)支持1..5圖片與OBJ選項，
不保證此設計的3D解剖或面流品質。

唯一待新增／更新的repo外檔案：

`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-hand-structure-20261003-001.dpapi`

依使用者先前「repo外檔案列出確切變更再授權」要求待人類授權。
只加密保存新任務恢復查詢資料，不含API主密鑰，不改舊任務、憑證或全域設定。
點數已按需授權；取得此檔權後，核對計畫／輸入／provider／同operation狀態，再提交一次，
追蹤同一任務並下載；pending／unknown不重送。完整命令仍經執行環境審批。

新phase四候選／每輪6h／總48h是本機實驗規劃，不是API花費上限。
前瞻時鐘在第一個r007準備步驟啟動，含量測、設計、review與基準，不重置r006。
r005與r006的1.5點服務回報與全部時鐘保留；本次圖片工具20.4＋17.9秒另記，金額未回傳。
兩手預算以目前57,039−2,742−左手估算537＋腕縫規劃256為54,016，
60k上限下兩新手合計規劃餘額5,984tri；左手未實切，所有生成實物與真正移除量仍需重測。

完整來源、可編輯骨架、300幀／60fps技能、獨立VFX與BLEND／GLB要求沒有降低。
最後本機完整性與工具檢查見[preparation-verification.json](preparation-verification.json)。
新來源、完整角色及最佳工作流均尚未驗收。
