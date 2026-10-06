# RO全手校準 r009 原型

**NO-SHIP／needs_revision／not_delivered**。以下均是局部右手診斷檔，並非完整角色或動畫交付。
沿用原Hyper3D手與r008拇指改善；新增API提交0、點數0。來源、舊失敗與成本保留。

| 檔案 | 實際內容與限制 |
| --- | --- |
| `baseline/right_hand_whole_calibration_baseline.blend` | 原r008v004逐byte副本；保留掌根壓縮與缺指接觸 |
| `v001-vectors/right_hand_full_vectors.blend` | 四指完整合法向量；同握姿掌根改善、接觸仍3/1/3/0/4 |
| `v002-coupled-IK/right_hand_coupled_contact.blend` | 耦合IK含三平移導數缺陷；失敗標本保留 |
| `v003-moving-target/right_hand_moving_target_contact.blend` | 移動target導數自檢通過；接近提案仍穿劍 |
| `v004-collision-constraints/right_hand_collision_constrained_contact.blend` | 碰撞約束保存姿勢：受測自交/劍交叉0，接觸3/1/3/0/3，未過 |
| `baseline/ro_whole_baseline.blend`、`.glb` | 原完整失敗baseline的副本，未整合本輪局部手 |

全手904點／894quad／1788tri；實際劍1493點／2552tri，原16手骨與sword骨。
469點域與86個四指cap修正；203拇指域、造型／UV／原16骨位保留；不同候選只作單一
剛性劍平移與控制角度。單位m，局部手座標，不可直接當成完整人物世界座標。
劍是靜態局部外物測試；骨名sword存在不代表interval掛接驗證完成。

v004新程序重開，核對原mesh／UV／權重／原骨位和未縮放劍，與同ID保存點做1微米
容差max/RMS比較。這證明保存內容可重現到受測容差內，**功能仍失敗**。
16跨UV島面未rebake；握持過程、左手、衣甲、300幀/60fps、獨立VFX及新動畫GLB未驗收。
勿以本檔替換accepted master。四候選已封存；stage、commit、push仍等人驗證。

請讀 `../../../runs/qa/ro-swordsman-combo-r009/README.md`、`fresh-saved-verification.json`、
`comparison-final.json`、`phase-accounting-final.json` 及獨立審查。沒有背景生成工作。
