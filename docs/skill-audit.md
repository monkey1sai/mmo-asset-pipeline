# 固定來源 Skill Guard 審查

日期 2026-10-02；來源 `arjun988/blender-skills@8f778d2405a214b508d4c7d80742be8e43acdd52`。

**CLEAN：本次納入範圍未發現惡意行為。** 範圍為 9 個技能目錄內的全部文件、9 個共享參考及 MIT LICENSE，共 34 個文字檔。每檔保留 SHA256，`verify-vendor` 檢查內容變動、缺檔或未鎖定檔案。這是固定版本的內容審查與完整性檢查，不是供應鏈數位簽章或未來更新的安全保證。

| 技能 | 結果 |
|---|---|
| blender-director | CLEAN |
| character-artist | CLEAN |
| retopology | CLEAN |
| rigging | CLEAN |
| animation | CLEAN |
| unity-export | CLEAN |
| environment-artist | CLEAN |
| export-pipeline | CLEAN |
| asset-optimization | CLEAN |

閱讀完整 SKILL 與各目錄 references，並檢查網路、執行、憑證、編碼、隱藏內容和越權指令。director 與其 routing reference 另與已完整讀取的本地內容比對，只有換行格式差異。已發現的外部連結是作者／Blender MCP 來源；`API keys configured` 是功能說明，不是讀取或傳送 key 的程式。

其中的 bpy 片段是已披露的 Blender 建模／匯出用途，仍受工作區與資產授權範圍限制。未執行上游程式、未複製 MCP 設定、未啟動下載或全域安裝。非本次選入的其他 85 個技能沒有本次 CLEAN 結論。

非安全問題另列為工程適用性差異：上游 director metadata 有重複 role；MCP 名稱只是示例；Unity GLB/importer、骨名、draw calls、UV／開口網格與 export 建議須以本 repo 與實際引擎能力為準。保留 upstream 原文，由專案入口覆蓋適用規格；不悄悄修改已鎖定來源。
