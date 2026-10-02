# 低摩擦迭代

設計師先用 PREVIEW 回答「這個剪影與材質是否值得做下去」。允許暫用低質 UV、來源 mesh、簡單綁定與替代材質；預覽包必須顯示未完成項、來源版本及尚未 production 驗收。階段標記不等於通過 technical gate。

| 改動 | 最小重建範圍 | 何時擴大 |
|---|---|---|
| 色票／roughness／shader參數 | 材質預覽、Unity 材質比較 | shader variant 或透明模式改變時加性能測試 |
| 不變拓樸的扣環／袖口位移 | Blender 存新版本、匯出受影響件、快預覽 | 權重、UV／烘焙失真或碰撞改變時補檢查 |
| UV 或貼圖細節 | 受影響貼圖／烘焙與shader輸入 | UV seam 或geometry對應改變時重烘焙 |
| 關節附近新增面／重拓樸 | UV／烘焙、蒙皮修正、變形測試 | bind pose 或骨架變化時做相容矩陣 |
| 骨長／rest pose／hierarchy | 新 rig/body variant、受影響服裝、Avatar 和動作 | 不接受用舊版本標籤掩蓋不相容 |
| 場景外飾／貼花 | 該模組視覺與局部性能 | navigation、collision或streaming bounds改變時做玩家路徑測試 |

快預览 target：記錄「從存檔到 Unity 可見」的秒數與失敗原因；先建立基線再設定團隊可達成的服務目標。first-pass auto weight、三視圖與shader placeholders 都可預覽，但 production 之前必須補完。

第一版尚未實作依賴快取／watcher／一鍵 Unity preview exporter。此矩陣是後續工具的重建設計，現有 planner 不宣稱能追踪模型依赖。
