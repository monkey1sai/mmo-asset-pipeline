# RO 劍士第二階段：失敗候選審查包

狀態：NO-SHIP／needs_revision。此包供壓力測試與使用者檢視，未通過美術、变形、連段或效果品質；未交付、未提交或推送 Git，沒有目標引擎驗收。

- `ro_swordsman_master.blend`：Blender4.5.5LTS可編輯 master，內含角色、骨架、動畫、可關閉效果與診斷 stage。
- `ro_swordsman_combo.glb`：只有角色與獨立劍／空鞘，內嵌PBR貼圖，59,340三角形、25關節、1skin。
- `ro_skill_effects.glb`：獨立展示效果，不是角色網格或遊戲規則；與角色載入同一場景、同一時間0..4.983333秒播放。
- `ro_repair_bind.blend`：保留開始完整動作前的預檢來源；attempt01/02/03保存早期失敗。

單位m；Blender+Z上/-Y前，GLB+Y上/+Z前。角色名義身高1.74m，含向上直劍的靜態bind最高1.84m。物件origin在角色根部，活動以骨骼綁定為準，不能把所有object origin視為各部位關節。骨架根`root`，依序`pelvis/spine_01/spine_02/neck/head`，左右`clavicle/upper_arm/lower_arm/hand/upper_leg/lower_leg/foot/toe/coat`，`sword`掛`hand.R`。實際座標映射見QA的`body-scale-rig-map.json`。

動畫`AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory`：60fps，Blender幀1..300，GLB匯入幀0..299，300幀播放5秒。不可僅因有通道就宣稱原作動作還原。效果在Blender的`COL_SkillEffects`，關閉render即取得無效果檢查；GLB是分離sidecar。沒有外部貼圖／BIN相依；來源圖與原raw保留於repo。

已知硬缺陷：255..300勝利站姿靴底離地約19/22mm；120..170支撐腳滑動；111..113持劍手/護手突變；GLB回讀肘甲與master有視覺差異；臉、腰甲、關節、衣襬及效果不達固定品質目標。六維3/3/2/3/2/2，比例較baseline退步，不可平均抵銷。

完整證據：`runs/qa/ro-swordsman-combo-r002/v003/`；`neutral-master-final`、`neutral-roundtrip-final`、`with-effects-final`各300幀與60fps影片。第一次穿頭失敗檢查保留於`neutral-master`，不被後續零交疊報告覆蓋。數值、縮圖、人類審查與實際遊戲runtime為不同證據。
