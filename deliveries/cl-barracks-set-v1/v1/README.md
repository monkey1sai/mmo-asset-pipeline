# cl-barracks-set-v1 / v1（delivery cl-barracks-set-v1-d1）

常山龍膽城池第一批環境資產：營房（`cl-barracks.glb`，節點 `barracks-body`、`barracks-roof`）、火盆（`cl-brazier.glb`，`brazier-body`、`brazier-coals`）、燃燒殘骸（`cl-wreck.glb`，`wreck-debris`、`wreck-embers`）。

- 單位公尺、+Y 上、+Z 前；每個資產原點在腳印中心、地面 y=0；節點 translation 皆為 0。
- 營房牆身 12.4×4.75×14.4（layout.ts 矩形 13×15 內縮 0.3，同 Web `castle.ts`）；屋頂外框超出矩形 1.225 m（`BARRACKS_ROOF_OVERHANG`），脊頂 7.57 m；屋頂為獨立節點，遊戲端依 `RoofCutaway` 隱藏。門在 x 較小側（東側營房朝城內）；西側營房實例化時繞 y 轉 180°。
- 火盆 1.15×1.32×1.15，炭火面為自發光材質；殘骸約 5.5×1.3×5.8（視覺散落大於 4.4 m 碰撞矩形，同 Web）。
- 材質：純色 Principled（roughness 0.85、metallic 0），無貼圖、無 UV；自發光節點 emissive 強度 1（實際 bloom 由引擎）。
- 三角形：360／36／288；材質：8／3／3；無骨架、無動畫、無 LOD、無碰撞體。
- 匯入：Unity 6000.6.4f1 以 glTFast 6.20.0 執行期載入（遊戲端 E10 驗收）；GLB 自含，無外部依賴。
- 製作：`assets/raw/cl-barracks-set-v1/v1/make_spec.py` → `spec.json` → `tools/blender/build_box_assets.py`（Blender 4.5.5 LTS）；預覽 `runs/qa/cl-barracks-set-v1/v1/previews/`；驗收證據 `runs/qa/cl-barracks-set-v1/v1/acceptance-evidence.json`。
- 狀態：delivered；目標環境（Unity 載入／測試）與鏡頭回歸已由遊戲端候選 3d725df 驗收通過，見 `runs/qa/cl-barracks-set-v1/v1/game/`。
