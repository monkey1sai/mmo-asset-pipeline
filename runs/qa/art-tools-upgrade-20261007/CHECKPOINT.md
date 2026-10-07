# 遠端工程 checkpoint

工具升級提交 `3ef92f64b3ff34b411a3c1f29cc176b4b66e3e76` 已推送 feature branch。首輪遠端 CI 沒有通過，失敗在既有跨平台測試 fixture，保留於 `ci-failure-01.json`；沒有降低 production guard 或以 skip 排除測試。

獨立 fixture 修復提交 `ea82ba436ae360c0b5a2f367c80535da76f9db0e` 的 [CI run 37591761561](https://github.com/monkey1sai/mmo-asset-pipeline/actions/runs/37591761561) 已完成：Linux 與 Windows 各 306 項完整測試、9 項 wrapper 測試，0 failed、0 skipped；Node 語法、路徑邊界、catalog／operation 及歷史 preview hash 也通過。

| 關卡 | 狀態與範圍 |
|---|---|
| Linux／Windows 工具 CI | PASS；精確 SHA 為 `ea82ba436ae360c0b5a2f367c80535da76f9db0e` |
| 原始 Beauty／Clay smoke | 歷史本機 Blender 4.5.5 擷取；本次遠端只核對 canonical protocol 與 script／PNG byte hash |
| 官方 Khronos GLB 結構驗證 | NOT_RUN；缺少官方依賴，wrapper 單元測試不代替資產驗證 |
| 新 gait／美術／runtime／P5 | NOT_RUN；此次 checkpoint 沒有新增 trial |

這個修復版成為新的工具工程基準；另以文件提交保存 [Git 管理流程](../../../docs/git-workflow.md) 與 AGENTS 入口。下一個 gait 工作從確認 CI 的最新文件提交起始，工具 source／既有 rig／rest／mesh／weights 與 cv1 門檻保持凍結，專注 pelvis、spine/thorax、shoulder、knee 和同條件 A/B。

目前 repo 的流程、階段與預算仍需按實際 ledger／clock 對帳；歷史 P4 失敗和 P5 未開始狀態保留。feature push 沒有合併到 main，也不授權後續 gait push、P5、付費或部署。

`engineering-baseline.json` 保存基準與每項主張；`remote-ci-pass-02.json` 保存同 SHA 的遠端 job／step metadata。原 `README.md`、`verification.json`、`installed-files.json` 是先前本機階段快照，保留原文；後續 AGENTS 的 Git-policy append 不冒稱與舊 whole-file hash 相同。製作增補／研究文件的原始「未執行」陳述也屬歷史盤點，最新工具執行狀態以本 checkpoint 為準。
