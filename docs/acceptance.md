# 證據與完成界線

| 證據層 | PASS 需要 | 不能推定 |
|---|---|---|
| 規畫 | brief 欄位、source lock／hash、可執行 planner | 有可用角色或 Unity 成品 |
| Blender 技術 | 實際讀 mesh／rig、三角數、UV、骨架 parent、真正 deform weights | 視覺形變正確、關節不穿模 |
| 視覺／形變 | 固定鏡位、极限姿势、材質與参考比較、不同裝備組合 | Unity 匯入／运行已通過 |
| Unity runtime | Avatar／Animator、換裝、socket、bounds／culling、LOD／collision的實際运行 | 發布或目標硬體效能 |
| 性能 | 指定硬體、畫質、同屏數、GPU/CPU time、memory、draw calls | 面數合格就足够流暢 |
| production | 以上适用項＋素材權利、來源與輸出 hash、完整交付包 | 付費或遠端發布授權 |

`inspect_asset.py` 僅提供 Blender 技術的子集。無模型、零面、缺 UV、必要骨骼缺失／parent 錯誤、未綁定、無 deform weights、超 influence 上限和 weight sum 錯誤都會失敗。報告包含真實來源 hash 和 Blender version；`production_status` 固定為 UNVERIFIED，技術 PASS 不會自動升級。

它尚不檢查完整的 UV 重疊、細緻 manifold／零面積、法線品質、actual T-pose、socket Transform、cloth、動畫視覺、貼圖尺寸、完整 LOD 鏈或 Unity importer。extra vertex groups 不算 deform bones；constraints 和 Geometry Nodes 需要在正式匯出時依專案設定烘焙。骨架 profile 名稱不是 bind pose hash。

硬甲可直接綁在有效骨骼，或經由 socket Transform 接到骨骼；檢查工具將這類 mesh 記為 rigid，不要求不必要的蒙皮權重。軟衣和身體才走 skin influence／normalize 檢查。此分類仍需實際動作與穿模驗收。

附件中的 `validate_fbx.py` 將所有 checks 寫成固定 `True`，是概念示範，未解析 FBX；不能拿來當 CI 證據。本版使用 Blender 真正讀取 `.blend`／`.fbx`／`.glb` 的資料。輸入用 background、factory-startup、disable-autoexec；`.blend` 開啟時 `use_scripts=False`。檢查僅輸出報告，不保存或覆盖來源模型。

本地 fixture 是合成 cube／rig 技術測試，不是用户資產、不評估美術或完整 MMORPG 可用性。測試不使用付費生成或外部私有素材。

完整交付包應記錄 asset/rig/body/shader versions、source／export hash、FBX、貼圖與layout、Unity prefab與版本、動作列表、換裝矩陣、截圖／錄影和性能報告。CI 先驗證實際能跑的 offline 工具；未建立、未跑過的自動匯出／烘焙／Unity CI 不可列為已完成。
