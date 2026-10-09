# 共用次級骨鏈本地入口

`scripts/secondary_motion.py` 是 Python／NumPy 參考求解器；`scripts/motion_workflow.py` 沿用 workbench request、identity digest 與 art_sources 路徑安全。角色差異放 profile，不改核心。這不是 Unity solver，也不是 Mixamo 官方 API。

```powershell
python -B scripts/workbench.py validate requests/secondary-fixture-v001.json
python -B scripts/motion_workflow.py --request requests/secondary-fixture-v001.json --profile configs/secondary_presets.json --trajectory configs/examples/secondary-trajectory.json --out runs/qa/secondary-demo-v001/result.json
```

輸出使用新版本路徑；已存在會失敗，不覆寫。CLI 退出 0 僅表示提供的軌跡數值約束通過，2 表示約束 FAIL；缺檔、非法設定或路徑錯誤皆失敗。結果綁定 request／profile／trajectory 的 canonical SHA，並保持 game_ready=false。

四種 preset 共用一個核心：披風柔性兩段、裙甲剛片一段、長髮柔性三段、飄帶柔性兩段。fixture 尺寸與數值不是已接受的武將設定。裙甲柔性內襯應另配 flexible 鏈；不要整件當軟布。

座標為 world metres；掛點為剛性 4×4 matrix，拒絕 scale、shear、reflection。body 動畫與 world matrix 更新 → anchor／proxy → fixed substeps → secondary local pose → skin palette → render；caller 負責實際骨旋轉與座標轉換。每組活動骨只有一個 writer。anchor 必須由 caller 外部先更新，不能是任一活動鏈的骨；此版本不支援鏈間依賴排序。

固定步預設 1/120 秒。沒有完成 substep 的幀，輸出點副本剛性跟隨當前掛點，不積分新力、不更動內部 fixed-step 狀態；下一個真正 step 再使用 caller 提供的掛點。caller 需要逐個固定步用相同動畫時間採樣，`advance` 不插值傳入掛點。結果包含長度、擺角、掛點誤差及代理穿入檢查，不只用步數判定 PASS。

pause 凍結模擬時間；顯示仍附著目前掛點。resume、clip 切換、瞬移、重生、旋轉跳變由 caller `reset=True`；大位移或超過 max_frame_dt 自動 reset。碰撞只涵蓋鏈端點與提供的 world sphere／capsule，不涵蓋布面、段中部、掃掠或自碰撞。多段剛片另驗全部節點間距；碰撞使剛片彎折時回 FAIL，不能當柔性衣料接受。目前不是完整剛體碰撞求解器，無法同時滿足的約束回 FAIL。

本入口只產生本地 JSON 點軌跡。Blender bake、動畫 clip 與 runtime 求解器設定是不同交付；GLB 不會自動攜帶可執行的風／彈簧／碰撞程式。合成 fixture PASS 不代表真實角色自然觀感、完整 DCC、引擎或遊戲接受。
