# 身體重定向與次級骨寫入隔離 checkpoint

整體 spec 仍為 **1/6、NOT_COMPLETED**。本次完成 D3 的合成工程 adapter 子項，不代表真實 Mixamo 整合或趙雲修復。D1 預算修訂尚未生效；Unity 完整遊戲驗收 NOT_RUN。

## 實作與輸入契約

沿用既有 identity、art_sources、embedded GLB 檢查及 GLB parser。新增共用 `scripts/rig_motion.py`：rest 相對旋轉、parent pivot 傳遞、剛性矩陣檢查及匯出動畫通道驗證。`scripts/blender_retarget_motion.py` 使用來源收據與 profile，重定向到 target 副本，不改 rest、骨名或層級。

此 adapter 支援單一 skin／armature、恰一個非空來源 clip、嵌入式 GLB、全段 identity armature object transform、in_place policy。來源 clip 名稱須與 motion 收據一致；多 clip、零 clip、名稱不符與後續影格物件／父節點的非 identity transform 都會拒絕。來源需先符合既有來源與公開原始素材審查契約；不能繞過 Mixamo 的公開原始再散布限制。非剛性矩陣、歧義骨名、root_motion 或其他未支援情形會拒絕。Source animation 在 CLI fps 下依 start/end frame 取樣；來源有約束、NLA 或其他資料格式的路徑未驗證。

Profile 格式沿用本地既有工具：

```json
{
  "source_to_target": {"source_body": "target_body"},
  "root_motion_policy": "in_place",
  "secondary_ownership": {"cape": ["target_secondary"]}
}
```

骨名只來自設定，不寫死角色。身體映射不得包含次級骨。Blender 匯出使用 ACTIVE_ACTIONS、非強制全骨採樣，並以實際 GLB `(node,path)` 檢查一個非空 clip、骨名唯一、只有已映射骨通道、沒有重複或未知通道。完成通道驗證後才記錄 secondary_tracks_authored=false。輸出 key 從 frame 0 開始；實際時間範圍須等於 `(end-start)/fps`。

## 操作入口

```powershell
blender --background --factory-startup --disable-autoexec --python-exit-code 2 --python scripts/blender_retarget_motion.py -- --request requests/REQUEST.json --receipt requests/source-receipts/RECEIPT.json --source-root SOURCE_ROOT --motion SOURCE_RELATIVE.glb --target assets/processed/TARGET.glb --target-sha256 TARGET_SHA256 --profile configs/PROFILE.json --out assets/processed/NEW_VERSION --start 1 --end 121 --fps 60
```

替換佔位值為已核對的本地來源；輸出必須是新版本。原始 source／target 不覆寫。產物包含 target 副本 `.blend`、baked GLB 與 report。這個 GLB 是已 bake 的身體 clip，不帶次級動態求解器；次級骨仍由獨立設定與遊戲端求解器負責。

## 已執行與保留失敗

- 舊四鏈 fixture v002 的重匯入 rest matrix 出現約 1.3e-5 至 4.9e-5 非正交誤差，NON_RIGID_POSE 拒絕；門檻維持不變。其材質與動畫接受不能由新測試替代。
- 最小原創三角形／兩骨 fixture 的舊 adapter v003 匯出兩套 clip、12 個通道，包含 target_secondary，為 FAIL。保留原始輸出與 log。
- v004 通道隔離正確，但實際 GLB 時間仍從 1/60 秒開始，與宣告零起點不符；121-frame readback FAIL 保留。
- 修正後 v005：一個 clip、三個 target_body 通道、無 target_secondary 通道。全新 Blender 5.2.2 LTS session 重匯入 121 個 frame，最大矩陣誤差 1.8898e-7、三個蒙皮頂點最大誤差 4.9747e-8 m、root 位置誤差 0、次級骨 local pose 誤差 0，target rest 誤差 5.9605e-8，層級相同，工程 PASS。
- CLI writer conflict、target hash drift、無效 frame range、既有輸出均拒絕（exit 2）。直接驗證舊 v003 也拒絕。單元測試另覆蓋偽造 secondary、未知／非法 target、歧義名字、多 clip、空 clip 與重複通道。
- 審查修正後 v006：新加入全段 object transform、來源 clip 數／名稱 guard，與 v005 相同條件再實跑；121-frame 矩陣及三頂點往返仍 PASS，GLB bytes 與 v005 同 SHA。新增後續 frame 31 才移動物件、多 clip、零 clip、收據名稱錯誤四項 Blender CLI 拒絕檢查均 PASS，未建立候選輸出。
- 本地藝術工作區 352 項 unittest PASS，checkpoint 分支 347 項 PASS；兩邊 pipeline validate 均 valid。既有六項重定向數學回歸另拆為 tests/test_rig_motion.py，公開 checkpoint 保留相同覆蓋；不是只保留本地歷史通過。
- Khronos 2.0.0-dev.3.10：0 errors、1 warning NODE_SKINNED_MESH_NON_ROOT。DCC 頂點往返通過不能替代其他引擎對 skinned mesh parent transform 的驗收；不將此 warning 記作完整技術接受。

v005／v006 GLB SHA-256：`54d1cf1f29395216bc501ad40b5ce334d4e87437ba8614de5ad6b08a5038f67c`。最新本地證據為 `runs/qa/retarget-clean-readback-v004.json`、`retarget-negative-v001/report.json`、`retarget-source-negative-v001/report.json`、同 bytes 的 `retarget-khronos-v005.json` 及各版 log；原創 fixture、診斷腳本與輸出保留本地。

測試收據使用 example.invalid 與 SYNTHETIC_TEST_NOT_LICENSE，僅驗證工程 schema 與流程，**不是人類素材權利核准，也不是可下載的外部來源**。沒有取得或匯入 Mixamo 動作。合成工程通過不證明其他武將美術接受或趙雲 game_ready。

## 後續與回滾

真實來源 adapter 使用、趙雲局部修復、四類部位視覺與動作接受、遊戲 solver 接入及 Unity 完整遊戲驗收均待執行。無法由工具 PASS 將 D3／D4／D5 結案。

可 revert 本 checkpoint 的 commit 撤回工具；原模型、失敗候選與歷史證據保留。沒有 runtime、付費、上傳、全域設定或 E12 量測器修改。
