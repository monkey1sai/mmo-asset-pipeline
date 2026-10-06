# RO 劍士 r007：掌腕來源先驗與貼身配裝

**新API來源已生成並下載；局部拇指面流可作新原型，掌根變形／UV仍未通過，完整角色NO-SHIP。**
原四候選已用4／4並關帳，compare=stop_budget、assess=not_ready，品質目標false。
本階段實際Hyper3D服務耗用0.5點，paid submit一次、download8檔；點數按需授權沿用，
本機四輪界線不是API額度限制。精確DPAPI檔權已獲人類授權、建立並實測綁定。
commit／push仍held，沒有staging；目前沒有API、Blender或reviewer背景工作繼續執行。
先前prepared文字與資料保留於[提交前README](README-pre-submission.md)、原準備紀錄與不可變API計畫。

## 目前實物與可證範圍

- [原生OBJ](../../../assets/raw/ro-swordsman-combo/rodin-v007/right-hand/base.obj)：
  1215vertices／1213quad／2426tri，沒有MTL；8項原始下載保留，
  [API完成核對](api-completion-verification.json)保存bytes／SHA、扣點與受支援恢復綁定。
- [局部quad patch](../../../assets/processed/ro-swordsman-combo-r007/v003-thumb-patch/right_hand_quad_patch.blend)、
  [實際線框](v003-thumb-patch/three-quarter-wire.png)：保留16點原生閉環，替換51面；814面位置與角UV保留。
  凍結CMC/MCP/IP帶內pole0，新cap4個非四價點放到IP軸向10.5mm；1834表面樣本最大偏差1.168mm。
  1788tri、18邊原腕口、中性橫向對／退化／新面反法線皆0。這只是幾何局部通過，
  [source_gate範圍更正](v003-source-gate-scope-correction.json)明列不等於所有來源關卡。
- [三骨拇指小動作](v003-skin-diagnostic/skin.json)：±.05rad實際表面位移方向已核對；
  .15／.30rad橫向診斷0仍有可見掌根折角。[UV島稽核](v003-thumb-patch/UV-islands.json)
  找到16跨原島新面，材質失敗，沒有做最終rebake。
- [最後權重BLEND](../../../assets/processed/ro-swordsman-combo-r007/v004-root-weights/right_hand_root_weights.blend)、
  [小屈側面](v004-root-weights/small030-side.png)、[小屈＋對掌側面](v004-root-weights/small030-opposition-side.png)：
  保留source geometry／UV／骨位／四指及遠端權重，掌根灰模仍有凹陷，不放行握劍。

| 候選 | 方法與實測 | 結果 |
| --- | --- | --- |
| v001 | 新來源、移除189內襯點、160次單步改線；彎曲帶pole4→2 | 來源面流失敗，不綁骨 |
| v002 | 72組兩步序列；帶內pole仍1，移動的3pole仍太近彎曲區 | 來源面流失敗，不綁骨 |
| v003 | 51面局部patch，帶內pole0；三骨±.05方向核對、小屈 | 幾何局部通過，16UV跨島面＋掌根形變失敗 |
| v004 | 3個有界鄰接權重域、每域100步；.30最大邊比2.078、.30+.15對掌2.306 | 側面形體失敗，關帳4／4 |

[獨立末輪覆核](v004-independent-review.json)確認權重方法缺口：把任何非零thumb02/03頂點
全部凍結，只解thumb01scalar，保留hand幾乎全權重→thumb02幾乎全權重的鄰邊突變。
原料/骨位未改前就不能把這個失败宣判為整掌拓樸不可用或再生成必要。
下一方法應先分出真正rigid cap與關節過渡，檢查完整骨鏈權重向量，隔離CMC/MCP/IP；
只有診斷指向結構不足，才重建掌根。原四輪不重開，原始時計與花費全部保留。
具體續作選項保存於[新方法草案](next-method-proposal.json)，status=draft_not_executed，
沒有第五個r007候選，沒有另立新phase或預先增加扣點。

本階段close wall9734.127367秒，含準備、等待、review與輪間規劃；
見[閉合比較](comparison-final.json)、[當前assess](assessment-final.json)、
[實際帳目](phase-accounting-final.json)。結案驗證的額外耗時另保存，不偽裝成重設時計。

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

[baseline綁定v2](baseline-binding-v2.json)及[準備時比較](comparison-baseline-v2.json)
是歷史revise_current_best／not_ready；[品質帳](quality-ledger.json)目前有四個失敗候選，
比較為stop_budget，quality_target_met=false。歷史ledger SHA由當時snapshot核對，
不把歷史證據說成最新mutable ledger。完整技能與材質等價的新GLB回讀未做。

## API、成本與恢復條件

operation：ro-hand-structure-20261003-001，generation_id：4da84074-918b-4473-89f1-bf2589a445e5。
兩張PNG、Gen-2.5-High、Quad、nativeOBJ、target1200、PBR high2K；
本次實際consumed0.5點，不以balance差額代替服務成本。
[非扣點預檢](api-preflight.json)當時authenticated=true、balance227.5；
[實際完成核對](api-completion-verification.json)於12:47:24UTC非扣點回傳balance227.0，分項未回傳。
這是該時間的餘額，不是未來即時聲明。提交後同operation查狀態，7job均Done，8檔已下載；
此任務nativeOBJ runtime已驗證，原始OBJ沒有MTL，依actualdiffuse與其他PBRmaps後製。
官方[Gen-2.5規格](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)支持1..5圖片與OBJ選項，
不保證此設計的3D解剖或面流品質。

本次已授權新增／更新的唯一repo外檔案：

`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-hand-structure-20261003-001.dpapi`

已由本次精確人類指令授權，[authority](hand-structure-authority.json)與API完成核對保留。
已建立並更新此934byte檔，只保存加密新任務恢復查詢資料，不含API主密鑰；
受支援provider实际binding驗證成功，不印出或保存plaintext。舊policy、provider、
主repo/API入口hash均未改；沒有改全域設定或舊任務，沒有重送pending/unknown任務。
codex doctor前後同一ENVIRONMENT_FAILURE：`elevated Windows sandbox provisioning recorded a structured failure`。
本次完整命令經個別執行環境審批成功；這不是全域doctor全部通過，也沒有修改安全設定。

主repo入口完整路徑：`C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py`。
本任務journal在隔離工作樹，查目前任務使用：

```powershell
python -B C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py --workspace C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop status --operation ro-hand-structure-20261003-001
```

已下載任務的status為本機完成紀錄，不是假稱再次即時服務查詢。新任務須先prepare、
核對唯一operation和需求，再依既有API授權與需要的精確repo外檔權提交。

新phase四候選／每輪6h／總48h是本機實驗規劃，不是API花費上限。
前瞻時鐘在第一個r007準備步驟啟動，含量測、設計、review與基準，不重置r006。
r005與r006的1.5點服務回報與全部時鐘保留；本次再0.5點，這三階段小計2.0點，
不宣稱全部專案總成本。本次圖片工具20.4＋17.9秒另記，金額未回傳。
兩手預算以目前57,039−2,742−左手估算537＋腕縫規劃256為54,016，
60k上限下兩新手合計規劃餘額5,984tri；左手未實切，所有生成實物與真正移除量仍需重測。

完整來源、可編輯骨架、300幀／60fps技能、獨立VFX與BLEND／GLB要求沒有降低。
準備時本機驗證保留於[preparation-verification.json](preparation-verification.json)，
本階段新檢查見[final-verification.json](final-verification.json)。工具測試通過不等於角色美術通過。
該紀錄截止13:35:39UTC；後續草案、README與主repo啟動命令另存
[補充驗證](final-verification-supplement.json)，沒有把稍後新增內容算入原297artifacts／79reports。
新來源的動畫用途、完整角色及最佳工作流均尚未驗收；staging／commit／push繼續held。
