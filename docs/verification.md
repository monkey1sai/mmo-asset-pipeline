# 本地驗證紀錄 · 2026-10-02

**VERIFIED：離線工具與固定來源整合完成。UNVERIFIED：正式資產製作及 Unity 端到端交付。**

| 實際檢查 | 結果與範圍 |
|---|---|
| Python 3.12.7，unittest | 11/11 PASS：brief、cloth／rigid 路由、profile 型別、來源變更、禁止覆寫、路徑範圍與未執行狀態 |
| Blender 4.5.5 LTS，實體 fixture | 11/11 PASS：blend 與 FBX 成功路徑；超面數、未綁定、缺 UV、權重總和、超 influences、非骨骼 group、錯誤 parent 的失敗攔截；有效 skin 與 rigid 均接受 |
| 固定第三方來源 | 9 個核心技能、34 個檔案 SHA256 相符，未納入其他 85 個技能或 MCP 設定 |
| 角色／建築／景觀 planner | 3 份規畫已產生；所有製作階段為 NOT_STARTED，production_status 為 UNVERIFIED |
| 專案 skill 格式 | 系統 quick_validate：Skill is valid |

Blender 回歸證據位於本地 `artifacts/blender-checks/b7563b0dfa70492986944825bb47b721/summary.json`，不進普通 Git。各情境檢查來源模型 SHA256 在檢查前後相同，確認檢查工具沒有修改原模型。單元測試臨時資料在測試結束由測試庫清除；本地 Blender fixture／預覽證據保留在 artifacts。

第一次 fixture 建立遇到 `AttributeError: bpy_prop_collection: attribute "clear" not found`，分類 TEST_FAILURE；已改用 Blender 支援的 UV layer remove，修正後完成上述回歸。此錯誤不是使用者資產或 Unity 的產品失敗。

尚未啟動 Hyper3D 付費生成、驗證供應商帳戶／餘額、安裝 Blender MCP、製作正式角色、實作自動權重轉移／烘焙／貼圖打包／Unity preview 外掛、執行 Unity runtime／shader／換装／同屏性能測試或發布 GitHub。這些不列為 PASS。

美術建議的 40%／80% 改善與 80/20 模組比例不是本次測量結果；前兩者需量測，後者僅為可調整的美術配方。
