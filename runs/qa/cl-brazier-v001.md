# 常山龍膽火盆 v001 驗收

狀態：`downloaded`／`needs_revision`，尚非 `game_ready`。

用途是 `src/world/castle.ts` 的重複火盆道具。生成目標為低面數三國風格鐵盆與石座，不包含火焰，動態火焰由遊戲維持。

## VERIFIED

- Hyper3D generation `c4fead7e-d088-4c2b-bc68-4efe5216a58b` 已 completed；實際扣月訂 0.5 點，普通點數沒有減少。
- 官方網頁 ZIP 已保存三個預期輸出，大小與 SHA-256 見當日操作紀錄。PBR GLB 為 6,942,464 bytes，2,500 個三角形，1 mesh／primitive／material，3 張內嵌圖片，0 skins、0 animations，沒有外部圖片依賴。
- Chrome 成品畫面可見靜態火焰、金屬支腳，與無火焰／石座 prompt 不符。畫面：`runs/evidence/20261002-cl-brazier-private.jpg`。
- 最終讀回 `Set asset public` 及閉合鎖頭，確認目前私有。操作中曾誤判標籤短暫公開，隨即改回並重新開頁驗證。公開期間有無第三方存取未核實。

## INFERRED

底座及火焰可能需要模型清理／部件分離，或以新的核准修訂方法處理。不能只關 emissive 就假定火焰幾何已移除。先保留 v001，避免付費盲重試。

## 尚未驗證

尺寸、公尺尺度、pivot、UV／法線、透明／發光材質、LOD、Collider、許可條款的實際交付適用、Blender 後製、Three.js 遊戲接入及 Unity 匯入。這次結構清點沒有驗證這些項目，沒有宣稱性能或 runtime 改善。

下一步由素材後製任務檢查火焰拓樸及底座，把衍生檔另存 processed；完整驗收後再提遊戲整合。此報告不授權改另一個 repo。
