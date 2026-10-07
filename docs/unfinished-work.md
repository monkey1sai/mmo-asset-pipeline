# 未完成工作與最新證據

更新日期：2026-10-07。此頁整理接手結果，不改寫需求、品質門檻或歷史授權。

| 項目 | 狀態 | 證據／下一步 |
|---|---|---|
| GLB 父節點 bounds | 已修復、8 regression PASS | `tools/glb_bounds.py` 與 `tests/test_glb_bounds.py`；三個營房套件交付輸出不變。 |
| 官方 glTF validator | 已安裝鎖定依賴、三個模型結構驗證通過 | `tools/art-validation/package-lock.json`；僅結構，不等於美術／遊戲接受。 |
| 營房門窗靜態視角 | 已補圖與獨立審查 | [集中接手紀錄](../runs/qa/session-consolidation-20261007/README.md)。保留尺寸描述歧義，Unity 未重驗。 |
| P4 角色閉環 | **FAIL，未修復** | [角色續作結果](../runs/qa/ro-swordsman-character-v1/continuation-20261007/RESULT.md)：baseline 18.731 µm、唯一候選 19.084 µm，門檻 10 µm；候選 discard、runtime 已恢復 baseline。 |
| gait 自然度 A/B | 未執行 | 需恢復原 ab-plan-v002 實物、核對 SHA／來源准入；92f8 worktree 已不可讀，不能把歷史摘要當已恢復的凍結契約。 |
| P5／holdout／角色交付 | 未完成 | P4 技術閉環尚未關閉；新候選需另有明確有界續作授權，舊耗用／失敗保留。 |

失敗候選程式只封存於角色 QA 的 `candidate-01-source/` 與 patch，不接入正式 runtime。原角色、骨架、權重、morph、reference、fixture 與 gate 未修改；局部數值改善與工具測試不得當作完整角色接受。

角色階段時計已結束：最多 2 小時／1 候選，實際約 30.6 分鐘、1/1 已用完。提交、push 及 worktree 清理由後續使用者明確授權執行，屬保存與維護，不新增角色試作。

主分支更新與兩個本次 worktree 的清理結果已記錄於 [維護紀錄](../runs/qa/repo-delivery-20261007/README.md)；其他工作與未知檔案保留。
