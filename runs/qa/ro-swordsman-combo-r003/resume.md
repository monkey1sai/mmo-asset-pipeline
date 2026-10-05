# 新版 API 續作點

使用者已明確允許本次壓力測試按建模需求使用所有可用 API 與現有月訂／普通點數，不設總點數上限；不加購或升級。commit／push 等使用者驗證成果。

使用者選擇新版入口，保留舊 `C:\Users\IOT\.codex\tools\hyper3d-api\authorization.json`。新入口完整路徑／MCP啟動資訊待提供；不要套用 `register_ro_apose_operation.py apply`，亦不要恢復或覆寫舊政策。

`generation-prepared.json`、`requests/ro-swordsman-combo-r003.json` 與 A-pose 圖已保存。舊工具唯一嘗試在輸入路徑驗證拒絕，沒有新task或扣點；余额228.5。新入口先核對schema、非扣點連線與目前餘額，再按需要更新該 prepared 的 backend／参数；保留舊prepared版本與拒絕報告，不換ID重送未知任務。

新raw下載到新版本，先完整baseline、再Blender細修／骨架／連段、五固定視角及完整功能檢查、逐維比較。旧r002正式baseline及3候選已保存，最後discard/stop_budget，不能再追加。新來源路線不得換掉舊r002品質參考或降低標準。

可用功能據本次schema：本機舊 adapter只有image_paths/High/Raw30k/GLB/PBR2K、balance/status/download；另一官方連接器有文生、圖片uploads、Raw/Quad、quality_override及完成asset的BANG，但帳戶／扣點来源未核對，不能假定與API key同帳戶。Texture-only、自訂模型BANG、Agentic在当前callable tools未暴露，保持未驗。依新版實際能力使用，不因官方文件提及就宣稱已測。

目前没有API任务、Blender渲染或后台排程继续执行。需要的输入仅为新版入口位置，不需要密钥。
