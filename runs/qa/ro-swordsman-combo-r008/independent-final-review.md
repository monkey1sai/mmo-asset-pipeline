已完成 r008 交付前唯讀審查。**`NO-SHIP／not_ready／stop_budget 4/4` 與目前證據一致，可以作為失敗原型關帳；不可作為完整角色或動畫交付。** 未發現素材庫誤登為 accepted／delivered、品質分數誤增或候選預算重置。另有兩项需要在最終摘要保留的證據限制，會影響下一方法選擇，但不需要為此重開候選。

**Scope**

本次讀取指定 README、關帳／比較／評估／重開驗證／下一方法提案、兩支腳本、素材庫 r008 entry，以及品質流程 r008 段落；直接檢視 `saved-best-palm.png`、`saved-best-side.png`、`saved-best-back.png`。只做檔案讀取、SHA256 核對與既有 JSON 摘要，未執行 Blender、產製、API、Git 或全域修改。本報告是 advisory，不是交付批准。

**Evidence — VERIFIED**

1. **四候選關帳正確。**[comparison-final.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/comparison-final.json) 列出 v001–v004 全部 failed、`candidate_trials_used=4`、`next_action=stop_budget`，保留原失敗完整 baseline 為比較基準；[assessment-final.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/assessment-final.json) 為 `not_ready`。`blockers=[]` 只表示比較紀錄沒有格式阻礙，文件未將其說成品質通過。

2. **383 次實测不是 480 次。**直接讀取 `v004-contact-solver/evaluations.jsonl` 得到 **383 行**，與 [v004-review.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/v004-review.json:5) 相符；480 是上限，固定 schedule 已完成。沒有利用剩餘 97 次宣稱還有第五候選，也未宣稱已證明全域不可解。

3. **保存端點接觸仍失敗。**重開記錄的固定 pad 接觸為 **3／1／3／0／4**，每指門檻為至少 3 點且距柄 ≤2 mm。無名指／食指第三近點約 **3.618／5.695 mm**。自交與劍橫向交叉均為 0、有限 inside 樣本最大穿入為 0，沒有抵銷缺指接觸。三張實際 PNG 也未呈現可放行的緊實包握。

4. **保存來源與歷史綁定成立。**本次直接計算 v004 BLEND SHA256，符合重開報告的 `6da16d01…196d282`。`phase-accounting-final.json` 所列六個 r007 保護檔的當前 SHA256 均與保存值相符。[verify_ro_vector_saved_best.py](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/scripts/verify_ro_vector_saved_best.py) 的實作確實核對原始 mesh／UV／來源屬性、權重、原 16 骨 head／tail、劍三角面與單一平移，並在不重新搜尋／擺姿下檢查保存失敗。

5. **registry 狀態與檔案存在性正確。**[library/index.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/library/index.json) 中 `ro-swordsman-combo-r008-v004` 只有一筆，為 `needs_revision`、art failed、delivery `not_delivered`，所列五個檔案全部存在。provenance 明確沿用既有 Hyper3D operation；r008 文件未把它寫成新的付費生成。

6. **時計與成本範圍清楚。**關帳 phase wall **3968.465451 秒**，baseline／準備及四候選時間合計一致；時計前 6.1 秒另列且未捏造最早起點。r008 新提交／新點數為 0 的階段紀錄與歷史 r005–r007 小計 2.0 分列，明示沒有本輪餘額查詢，也未將歷史小計稱為完整專案總成本。

**Finding — 需要保留的兩項具體限制**

1. **重開後求值頂點並非逐值完全相等；目前只確認失敗關卡重現。**  
   [fresh-saved-verification.json:3272](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/fresh-saved-verification.json:3272) 明確為 `point_fingerprint_equal=false`。原求值指紋為 `2582adfa…ba1f`，重開為 `e270f367…00a`；最大邊比由 `2.1582470655` 到 `2.1582526179`，最大絕對邊長變化由 `0.010771209588 m` 到 `0.010771203360 m`。

   這些彙總差異很小，**但尚不能據此斷言所有頂點差異都只是浮點誤差**。README 現有「重現接觸失敗」用詞合理，請維持這個範圍；建議最終摘要加一句「求值頂點指紋不同，未驗證逐點等價」。若以後需要宣稱形變等價，再補同 ID 的逐點最大／RMS 差與容差，無須為本次 FAIL 關帳重開搜尋。

2. **保存姿勢除了接觸不足，仍有明顯壓縮的數值證據，下一階段不應只追兩指接觸。**  
   [fresh-saved-verification.json:47](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/fresh-saved-verification.json:47) 記錄最小邊比 **0.0665655768**。具體 edge **277–278** 從 **8.9174 mm** 縮為 **0.5936 mm**，縮短約 **93.34%**；edge **372–388** 從 **13.7605 mm** 縮為 **2.9893 mm**，最大絕對變化 **10.7712 mm**。這與先前掌根兩側接近 hand／finger1 剛性權重的觀察相呼應。

   這是嚴重局部壓縮的證據，尚不是單憑邊長就完成的體積／拓樸診斷。應在 `v004-review` 或最終摘要把它列為下一階段的固定檢查位置。不可把「只差無名指／食指接觸」解讀為其餘形體已驗收。

**Uncertainty／Risk**

- 本次沒有重跑 119 tests 或 39 筆清單驗證；這些是主控現有驗證紀錄，不是本審查新執行的測試。測試、schema、檔案完整性與資產美術通過仍須分開。
- 橫向交叉、有限 inside 樣本、polygon 截面／凸包的限制已在 README 與流程文件披露；不能推論完整無碰撞、無鄰接折疊或體積合格。
- 16 跨 UV 島面仍 FAIL；握持區間、左手／衣甲、300 幀／60 fps、獨立 VFX 與新動畫 GLB 均未通過或未執行，文件沒有用局部靜態原型替代它們。
- `final-verification.json` 正由主控產生，本審查未把其暫時未完成當作資產或關帳問題，也未預先宣稱其通過。

**Next**

[next-method-proposal.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r008/next-method-proposal.json:12) 可以作為人類選擇的草稿：它明示若調整四指權重、骨心或局部 mesh，需要新 phase 允許解除相應凍結；也保留同幾何有界 IK 與重新生成兩種方向，未自動執行第五候選。

建議把推薦方向表達為：**先定位掌根壓縮及各指接觸可達性，再決定必要權重、骨心與 MCP／虎口面流修改。**目前證據尚未證明所有骨心都錯或一定要重拓樸；若診斷需要重建，應如實視為 substantial production，保留來源外觀／貼圖並重新驗證幾何、UV、功能與後續動畫，不能許諾只是微調。

主控完成最終驗證後可交付這批 **NO-SHIP 診斷成果與待選提案**。r008 維持 4/4 closed，不擴展產製。本審查目前沒有背景工作繼續執行。
