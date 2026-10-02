# 交付包

已驗收資產存 `deliveries/<request-id>/<version>/`，模型與貼圖依 `.gitattributes` 用 LFS，README／manifest 用一般 Git。此文件定義保存方式，目前沒有新的已交付模型。

每包包含需求指定輸出、相依材質／貼圖、預覽及 README。README 記用途、尺寸、軸向、pivot、部件、材質／貼圖通道、骨架／動作、匯入方法、限制與實際驗收範圍。獨立資產不宣稱 Unity 可用；需求指定環境才列實測版本與情境。

`manifest.json` 至少記 `schema_version`、`request_id`、`request_sha256`、`asset_id`、`version`、`delivery_scope`、`source_versions`、`files`（repo 相對 path、bytes、sha256）、`acceptance_record`、`known_limitations`。來源有 commit 時記完整 SHA；初始化尚無 HEAD 不捏造 commit，用來源操作 ID 和檔案雜湊追溯。

登記所有外部依賴，包括 OBJ 的 MTL、glTF 的 BIN／貼圖；驗證引用為包內相對路徑。`package_complete` 的實際檢查要證明依賴與說明齊全，程式不自動解析相依圖。保留 master 與後製檔，交付審查通過才更新 `library/index.json` 的版本與完成狀態。

交付資料隨 repo 保存，本機納管與遠端同步／移機還原分開驗證。參見 `docs/asset-storage.md`。
