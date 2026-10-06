# 獨立新階段準備覆核

Reviewer：`/root/hand_phase_review`，唯讀；依適用task-routing要求以Astra/high派送。
Requested model為`gpt-6-astra`、high；派送工具接受指定，但沒有額外的runtime模型讀回。
未修改檔案、執行產製、花費、讀憑證、操作Git或控制Blender。

覆核已讀r006需求、phase-start、generation-prepared、api-preflight、api-spec-hand、
手套設計圖，以及r005README／指軸更正／v003最終覆核、rig helper及新階段準備脚本。
初次sandbox啟動失敗後，維持既有命令工具，窄範圍唯讀經審批執行，未改安全設定。

已確認完整60,000tri、300frames/60fps、可關閉VFX、BLEND／GLB及回讀要求不變；
r005三次失敗、14,607.710521秒及1.0點服務回報保留。新階段時鐘與先前未instrumented
規劃時間有分開；非扣點预檢記錄228只是當時總餘額。新operation為prepared，
DPAPI精確檔權限仍等待人類，不能提交。

設計圖可作生成輸入，但未提供手背、側厚度或關節迴圈的3D證據。
獨立手套降低皮膚／硬甲耦合是推論，不代表腕縫、護臂或衣物穿插已解決。

覆核提出兩項實作前修正：

1. 固定局部手部姿勢、近照、指墊與真正劍柄、接觸／穿透、面交叉及UV／腕口關卡。
   已補`hand-gate-contract.json`，由`baseline-binding.json`保存SHA；沒有降低完整品質目標。
2. 先量測舊手移除量，再規劃雙手及腕縫面數，不能把API target當實測tri。
   已以實體Blender取得`hand-budget-scout.json`：58868 −492 −537 =57839；
   預留256後每手952tri。必要硬甲減面另存衍生版本並驗固定五視角。

覆核未執行新模型、Blender、碰撞、300幀或GLB回讀；沒有成品SHIP結論。

## 修正後窄範圍覆核

同一獨立reviewer再次唯讀核對新增關卡、面數量測、baseline、技術量測、評分、
品質帳及工作流／skill文字；實際重算四份綁定SHA相符。
已確認58868−492−537=57839，以及預留256後每手952tri的算術正確；未切除模型。
檢視three-quarter、grip-R/side、grip-L/palm三張真實圖，觀察與NO-SHIP描述一致。
尺寸／映射pass保持局部範圍；匯入與效果明列runtime:not_run，没有冒充執行測試。
未重新執行Blender或独立重算接觸數值；這些限制保留。
結論：兩項準備問題已補齊、沒有新增實質阻礙，可在取得精確外部檔權後接續既定流程。
