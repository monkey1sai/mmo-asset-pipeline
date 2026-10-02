# EvoLoot 基礎鐵劍 v001 驗收

狀態：`downloaded`／`needs_revision`，尚非 `game_ready`。

用途是來源 `EvoLoot/domain/entities.py:519` 的基礎鐵劍及 Neutral 活體武器外觀。目標是簡單可讀、單一鐵刃、磨舊皮革握柄，作為五人格家族的共同基礎。

## VERIFIED

- Hyper3D generation `4574e81b-b870-4b71-a066-9b557b36ab9d` 已 completed。實際耗 0.5 點，API 229.5 → 229；成品頁 wallet DOM 月訂 204、普通 25、凍結 0。
- 官方 Chrome 匯出 ZIP 已下載；兩個預期 GLB 檔案用不覆寫方式保存。PBR 是 11,979,684 bytes、1,800 個三角形、1 mesh／primitive／material、3 張內嵌圖片、0 skins、0 animations；沒有外部圖片依賴。
- 成品頁讀回 `Set asset public`，畫面為閉合鎖頭，保持私有。沒有切換可見性。
- 視覺結果有雙叉刃、大面積金色護手與飾件，與簡單、鏽鐵單刃的目標不一致。畫面在 `runs/evidence/20261002-evoloot-iron-sword-private.jpg`。v001 保留為造型候選，不採為 Neutral 定稿。

## INFERRED

文字生成不能可靠保留這次要求的刃形與色盤。下一筆相同家族素材宜先建立明確單物件視覺參考、選定幾何與後製方案，避免盲目付費重做。1 mesh 不代表握柄或刀刃已分離。

## 尚未驗證

公尺尺寸、刃朝向／握點、UV／法線、材質貼圖品質、LOD、Collider、許可條款交付適用、Blender 後製、Godot／Three.js／Unity 匯入或遊戲實測。2K 匯出是網頁選項，清單 1K 是後製目標；目前沒有宣稱實際圖片邊長驗收或縮小貼圖。

下一步在獨立版本中修訂刃形與材質，先做原創參考及後製驗收，不改動 EvoLoot 既有 2D 畫面或玩法。本報告不授權其他 repo 寫入。
