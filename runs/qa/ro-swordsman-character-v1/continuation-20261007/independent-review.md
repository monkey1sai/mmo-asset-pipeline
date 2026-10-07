# 獨立審查紀錄

Reviewer：`/root/takeover_plan_review`，read-only architecture_reviewer。實際進行 pre-plan、recurring-failure 與 pre-delivery checkpoints。

Pre-plan 接受在 2 小時／1 候選／原門檻內調查。要求原 reference JSON/bin、foundation、fixture、10 µm 保持不變，且候選須全 118 references 回歸。

Pre-delivery **reject**，候選 `failed / discard`，保留 baseline（baseline 自身仍 FAIL / NO_SHIP）。Reviewer 直接讀兩份完整 runtime JSON、候選 source、測試與 preservation 記錄；獨立核對 7 份候選 harness SHA。未獨立重跑 4 Node／306 Python tests，也未重新雜湊全部 47 份 protected inputs；這些是主控執行證據。

| 項目 | Baseline | Candidate |
|---|---:|---:|
| references | 118 | 118 |
| 通過／失敗 | 116／2 | 116／2 |
| 最大誤差 µm | 18.731347653 | 19.083941248 |
| 每筆失敗的超標匯出頂點 | 1,751 | 1,759 |
| 其他 verdict | 7 true | 7 true |
| negative controls | 4 detected | 4 detected |
| determinism 最大差異 | 0 | 0 |

Source finding：候選只把 pre-IK 位置改為 affine FK；旋轉仍從 rendered TRS 的 `getWorldQuaternion` 取得，再透過 quaternion parent inverse 寫回。這是表示混用的具體區段，尚未證明它是剩餘誤差的唯一根因。只能作下輪待驗假設，不能以剩餘時間追加第二候選。

審查讀取時候選接線仍啟用、ledger 尚 pending。審查後主控已將當時完整三份 source 保存至 `candidate-01-source/` 並核對兩份 runtime source 與 run SHA；用明確 apply_patch 恢復 baseline，不用 reset/clean。恢復後 `p4.js` SHA 為 `8b661ccd444787b0b6843241f753eae6b9825b247f20658cd43c7ec347c1f6e8`，與 baseline 逐位元相符。這個恢復核對是主控確定性證據，不冒稱 reviewer 已讀到恢復後狀態。
