# RO 劍士 r008：局部手模型與接觸診斷，NO-SHIP

本階段沿用已下載的Hyper3D來源，修完整拇指骨鏈權重及CMC旋轉方向，再做大幅度
手部與真實劍接觸測試。四個候選已封存，完整角色、骨架與300幀／60fps連續技能仍
未完成。這些檔案是可檢查的局部原型，不是可交付master；沒有stage、commit或push。

| 檔案 | 實際內容與狀態 |
| --- | --- |
| `baseline/ro_weight_vector_baseline.blend`、`.glb` | 原失敗全角色的byte相同副本；57039tri、53骨、61幀握持原型，不是300幀技能 |
| `v001-vectors/right_hand_vectors.blend` | 1788tri右手、16局部骨；完整拇指權重，CMC旋轉方向首輪失敗 |
| `v002-direction/right_hand_vectors_direction.blend` | 同一手的旋轉方向修正；小幅有符號測試通過受測子範圍，大幅功能姿勢仍失敗 |
| `v003-digit-control/right_hand_actual_sword_control.blend` | 真實來源劍2552tri，各指独立控制；保存選定的失敗切穿姿勢 |
| `v004-contact-solver/right_hand_actual_sword_best.blend` | 383次有界實測後的無交叉診斷姿勢；無名指、食指接觸不足，不能交付 |

使用Blender4.5.5LTS開啟局部檔案即可查看。`SM_RO_RightHand_Exterior`為手，
`ARM_RO_HandDiagnostic`為局部骨架；後兩檔含`SM_RO_LocalActualSword`及對應weapon骨。
本地手是+Z向指尖、-Y掌面、+X拇指；不是角色或GLB的最終坐標設定。保存貼圖沿用來源，
16個新面跨UV島缺陷仍存在。灰模QA圖拿掉貼圖與效果，不以材質掩蓋功能問題。

最後檔案手geometry、每角UV、來源ID、權重與原16骨head/tail經新Blender程序實測
一致；劍只作一個剛性平移，未改尺寸與原三角面。保存握位平移為
`[-0.00375,-0.043,-0.034]m`，完整角度與矩陣在QA報告。沒有動畫、GLB或人體配裝的
新通過證據；既有baseline GLB不得當成r008已完成動畫。

| 接觸部位 | 距實際劍柄<=2mm的固定pad數 | 必須至少 |
| --- | ---: | ---: |
| 小指 | 3 | 3 |
| 無名指 | 1 | 3 |
| 中指 | 3 | 3 |
| 食指 | 0 | 3 |
| 拇指 | 4 | 3 |

實際橫向自交0、手—劍交叉0、sample穿入0仍不能抵銷缺指接觸。檢查方法排除相切、
共面與共享點鄰接折疊，零不是完整無交叉證明。端點未通過，握持區間、UV rebake、
左手、衣甲接合、300幀技能、独立VFX及完整動畫GLB重匯入都未展開。

詳見`../../../runs/qa/ro-swordsman-combo-r008/README.md`與實物綁定報告；
原始Hyper3D來源在`../../raw/ro-swordsman-combo/rodin-v007/right-hand`，舊r007來源和
全部失敗保留。r008新增付費提交0、點數0，未改全域API憑證或任務恢復檔。
