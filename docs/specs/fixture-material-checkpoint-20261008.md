# 次級動態 fixture 材質工程 checkpoint

整體 spec 仍為 **1/6，NOT_COMPLETED**。D0 診斷已閉合；D1 真實角色修復、D2、D3 Mixamo、D4 真實動作與 D5 Unity 完整遊戲驗收均未完成。

## 問題與範圍

既有本地四 preset fixture 的 Blender 材質只設定 diffuse_color，匯出 GLB 後變成灰色。此次明確設定 Principled BSDF 的線性色值、金屬度、粗糙度與 alpha，使用 Blender 原生 glTF 匯出及匯入驗證。

本 PR 提供獨立可執行的共用 helper 與材質專項檢查。尚未納入 main 的次級動態 fixture 產製器已在本地改用此 helper；該產製器不在本 PR 範圍。沒有重跑完整動畫候選，也沒有改寫 v001/v002 舊資產、失敗證據、趙雲模型或遊戲 runtime。此檢查不重設既有美術 trial／時間預算。

## 操作入口

在 repo 根目錄，以獨立 Blender session 執行：

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 2 --python scripts/blender_fixture_material_check.py -- --out runs/qa/fixture-material-roundtrip-v001
```

Blender 位置依本機安裝調整。輸出位置必須是 repo 的 runs/qa 下，已存在則拒絕。輸出 material-only.glb 與 report.json；重新執行請使用新的版本路徑，不覆寫證據。

## 實跑結果

- Blender 5.2.2 LTS，2026-10-08：四組 fixture 色值及 `(0,1,0,1)` 邊界值，GLB JSON 與清空場景後重匯入的 shader 值，誤差均小於 1e-6，PASS。
- RGB 少一通道、NaN、負色值、alpha 大於 1：四項均拒絕為 INVALID_LINEAR_RGBA，PASS。
- 本地 material-only.glb SHA-256：`f8b1ce0eddb0d4a968c0c96aa2e502f38d9f0bd433c649384eb663ac1e6ba4fd`。
- 本地完整工具測試 344 項 PASS；`scripts/pipeline.py validate` 為 valid。CI 及 checkpoint 分支測試另記於 PR。

這不是整套動畫往返通過，也不是自然觀感驗收。實際 Mixamo 整合、真實角色 DCC 修復、Unity runtime 均為 NOT_RUN。GLB 不帶可執行次級動態求解器。

## 下一步與回滾

真實角色 D1 仍需要核對既有預算及可安全修訂的部位遮罩；保留既有修復授權。完整 fixture 重產與動畫往返需沿用原 trial 紀錄，不能因本 checkpoint 另起分支而重新計數。

撤回本工具可 revert 本 PR 的 commit；舊資產及證據不受影響。只有 D0–D5 全部符合 spec，尤其 Unity 完整遊戲驗收通過，才能稱為 spec completed。
