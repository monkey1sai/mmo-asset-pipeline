# 製作基準之前的幾何失敗

兩次本機建造失敗分類 `TEST_FAILURE`（匯出前幾何驗證），均未匯出 GLB，不能當品質 baseline 或通過。

1. 未封口 bevel curve 轉網格：`SM_PlateCentralRidge`、兩眉、嘴、兩衣襬鑲邊、白襟鑲邊，各 16 nonmanifold edges。
2. 啟用 `use_fill_caps=True`：同七部件各 32 nonmanifold edges，說明封口未與侧面頂點連接。

新方法：轉成 mesh 後焊接距離 `1e-7m` 的共位頂點，重算法線，再以 BMesh 逐網格檢查所有邊為 manifold。這不跳過門檻；不合格仍不得匯出。兩次失敗及準備時間納入 baseline 耗時。已交獨立唯讀診斷。其餘部件當時未報非流形；這不代表造型／關節／動畫已通過。
