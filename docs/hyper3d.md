# Hyper3D／Rodin adapter

本次已發現官方連接器 `rodin_generate`、status／wait／result 與 `rodin_generate_bang`，以及本機 DPAPI-backed API adapter。沒有啟動生成、上傳、讀取憑證或下載既有任務。Blender MCP 在本次 callable tools 中未發現；本地 Blender 4.5.5 LTS 可執行離線檢查。

## 授權與工作生命週期

具體提交前記錄：destination、資產／prompt、獲准上傳的參考圖、最大 credits／候選數、允許操作、禁止操作與停下條件。設定固定重試上限，submission timeout／未知 accepted 状態時先查既有任務，不重新送單。服务 error、非空 generation id 與 status 必須真實查證。

`PREPARED → AUTHORIZED → SUBMITTED → PROCESSING → COMPLETED → DOWNLOADED → BLENDER_REVIEWED`；生成失敗或提交未知分別保留 FAILED／SUBMISSION_UNKNOWN。completed 只代表供應商任務完成，不代表 production-ready。記錄 permanent display URL、generation ID、参數與下載檔 SHA256；憑證、subscription_key 與臨時 signed URL 留在受支持憑證／會話机制，不提交 repo。

## API 與 connector 分開

官方 Gen-2.5 API 支援文字或 1–5 張參考圖，Raw／Quad、quality、FBX／GLB 等。此環境官方 connector tier 可用 Medium／High／Extreme-Low，Raw polygon target 500–1,000,000，Quad 1,000–50,000；以當次工具 schema 為準，不把 HTTP API 的更大範圍塞進 connector。API 文件還列出 TAPose，但目前 connector schema 沒有該欄位；用明確 pose 參考和 Blender 整理，不能宣稱已送 TAPose。

Quad 只表示候選拓樸類型，不能證明關節 edge loops、分件、蒙皮或可換裝。BANG 是付费的分件候選服务；自動拆件仍需 artist 確認拆分界線、UV／材質、裝備掛接與內部面。BANG 不替代 rigging／skin weights／cloth。

官方 API 文件目前列出基礎 Gen-2.5 0.5 credits、BANG 0.5 credits，特定高階參數另加費用；這只是 2026-10-02 文件值，實际執行前必須檢查所用 backend 當前報價／餘額和用户預算。兩個 connector 的費用與能力不可混為一個。

prompt 作法：描述單一資產或明確部件、轮廓、尺寸關系、材質、rest pose、手腳分離與避開背景；人物、服裝和武器分別安排候選，避免只產生整件不可拆的雕像。prompt 不能保證輸出满足這些要求，下載後仍需實际檢查。

來源：[Gen-2.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)、[BANG](https://docs.hyper3d.ai/en/api-specification/bang)、[Quick Start](https://docs.hyper3d.ai/en/get-started/quick-start)。
