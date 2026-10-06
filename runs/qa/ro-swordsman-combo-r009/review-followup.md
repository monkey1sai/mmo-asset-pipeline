# r009 最終獨立審查追加說明

`independent-final-review.md` 保存 `/root/hand_phase_review` 的完整原樣報告（Astra/high）。
Jev before-delivery確定性觀測 `7b83fc83-dd11-4dd7-8591-71aa3eff59f1`；provider未呼叫，
執行未由路由工具啟動。審查是advisory，不是交付批准。四候選仍關帳、NO-SHIP。

**診斷命名更正：保留原JSONL／程式／報告，不回寫失敗。**

1. `v003-moving-target/jacobian-observations.jsonl` 與 `v004-collision-constraints/jacobian-observations.jsonl`
   的 `predicted_delta` 是 `-J.T @ residual`，應解讀為**負梯度**；不是經阻尼矩陣求得的未約束步，
   也不是v004投影後的實際控制步。v004的實際正規化約束步見 `collision-constraint-observations.jsonl`
   的 `normalized_delta`；實際提案參數與採用结果見evaluations，不用負梯度重播姿態。
2. `max_halfspace_violation_m` 混合近表面距離列（m）與正規化控制box列（無因次），應解讀為
   **混合約束的最大殘差**，不是物理最大穿入距離。該欄數值不能直接與mm深穿入門檻比較。
   真實有限樣本穿入引用final_contact/fresh.contact，完整提案仍另驗三角交叉；本次無宣稱代理等於碰撞PASS。
   未來方法需分列距離殘差、box殘差及容差，此次不重開搜尋。

受測同握姿掌根改善僅限這次條件；不宣稱所有掌根姿勢已修復。904點最大/RMS差為0也只涵蓋
本輪保存姿勢，不回溯r008、不能代替全部動畫。

**下一草稿限制：**查語義pad覆蓋、法線與指節接觸，不得換近點降低原關卡；若確認舊mask錯誤，
保存更正依據與舊結果。美術設計的接觸targets只引導控制；姿勢修正形變是新製作工作，需限定部位、
原形偏差、過程與匯出驗證，不能把指腹投到柄上就稱PASS。沒有證據要求所有骨心搬移或重新生成。

v004 index82總第三近gap比index57改善0.188017mm，最差卻退0.004614mm而被lex排序拒絕；
這是已驗的方法停滯，不是模型無解。保留所有原型、來源、183歷史檔與時計，stage/commit/push held。
獨立審查、Blender、API皆已結束，沒有背景工作繼續執行。
