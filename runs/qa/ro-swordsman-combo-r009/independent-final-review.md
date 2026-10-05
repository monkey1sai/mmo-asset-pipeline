已完成 r009 最後獨立唯讀審查。**`NO-SHIP／not_ready／stop_budget 4/4` 與保存實物及評估記錄一致，可作為未達交付的診斷成果關帳。** 未發現誤增完整品質分數、把局部握姿宣稱為 300 幀交付、重置候選預算或覆寫受保護歷史。另有兩個診斷欄位的命名限制，以及下一提案的範圍需保留；它們不改變本輪 FAIL，也不需要新增候選。

**Scope**

本次閱讀指定關帳文件、ledger、v003／v004 程式與報告、保存驗證程式、素材庫最新 entry、品質流程 r009 段落及下一方法草稿；直接查看 v004 `saved-best-palm/side/back.png`。執行內容限於讀檔、記錄分類和 SHA256 核對，未執行 Blender、產製、API、Git 或全域修改。本報告是 advisory，不是交付批准。

**Evidence — VERIFIED**

- **四候選與時計保存一致。**[comparison-final.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r009/comparison-final.json) 為 4 個 failed candidates、`stop_budget`、`quality_target_met=false`；[assessment-final.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r009/assessment-final.json) 為 `not_ready`。完整失敗 baseline 仍是品質比較基準，沒有將局部原型升格為 accepted master。階段 **1837.115223 秒**與 baseline／準備及各候選時間合計相符；首次時計前的準備明列未精確量測。

- **實測次數沒有混成全功能驗證。**本次直接讀取三份 evaluations：

  | 候選 | 全部探測 | 完整功能檢查 | 導數／基準／自檢 |
  |---|---:|---:|---:|
  | v002 | 83 | 11 | 72 |
  | v003 | 36 | 5 | 31 |
  | v004 | 86 | 7 | 79 |
  | 合計 | **205** | **23** | **182** |

  README 與 accounting 的分類正確。v001 24 組只宣稱正向 .05／.30，沒有擴称反向伸展。

- **v002 的缺陷與 v003 修正均有實證。**v002 在 ledger 保留 `TEST_FAILURE`，沒有退回預算。v003／v004 的正負 xyz 自檢手點最大位移為 0，殘差誤差最大約 **1.829e−8 m**，低於 `1e−7 m` 容差；正規化平移欄對 −.03 的最大誤差約 **2.743e−6**，低於 `1e−5`。程式確實使用隨 weapon shift 移動的 target，並保存實際使用的 guide IDs 與 targets。導數通過沒有被寫成握持通過。

- **v004 的零受測交叉與接觸失敗同時成立。**7 個完整檢查案例，包括初始狀態與 6 個 proposal，均記錄手內／手—劍橫向交叉為 0；保存端點仍是 **3／1／3／0／3**，未達每指至少 3 點、距柄 ≤2 mm。無名指／食指第三近點距離為 **3.047245／3.092480 mm**。三視圖仍顯示鬆散握位，沒有支持完整包握的視覺證據。[v004-review.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r009/v004-review.json) 維持 FAIL 合理。

- **這次保存／重開的逐點驗證補上了 r008 的缺口。**[fresh-saved-verification.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r009/fresh-saved-verification.json) 記錄 904 個同 ID 求值點，最大／RMS 差均為 **0 m**，低於 `1e−6 m` 容差。[verify_ro_whole_saved_models.py](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/scripts/verify_ro_whole_saved_models.py) 實際核對幾何、UV、來源屬性、v001 權重、203 點拇指保護、原骨 head／tail／parent，以及未縮放劍三角面與平移誤差。此結論限於這次保存姿勢，不回溯補成 r008 逐點等價，也不是其他姿勢或動畫等價證明。

- **歷史與登錄正確。**本次獨立重算 **183 個 protected history 檔案，0 個雜湊不符**；v002／v003／v004 BLEND 雜湊也符合各自 result。素材庫 r009 entry 為 `needs_revision`、`not_delivered`，明示原型、接觸失敗與未執行項。新增 API／credits 0 與沿用既有來源分開記錄，未宣稱本輪查過即時餘額。

**Finding — 方法停滯的描述有實際依據**

v004 接受到 index 57 時，最差第三近點距離為 **3.092480 mm**、五指第三近點距離總和為 **10.738587 mm**。下一個完整 proposal（index 82）沒有受測交叉，總和改善至 **10.550570 mm**，但最差值變為 **3.097094 mm**。

也就是總和改善約 **0.188017 mm**，最差值退步約 **0.004614 mm**，因此被字典序比較拒絕。README／提案所述「有合法提案改善總 gap，但被最差 gap 優先的目標拒絕」是可核對的事實。它證明目前接受規則造成停滯，**不能證明模型全域不可達、骨心錯誤或必須重新生成**。

v004 的最多 96 個近表面頂點／邊中點／三角中心代理及半空間投影，是局部提案方法。完整 proposal 仍經實際三角面、inside 與固定 pad 門檻檢查，沒有把代理可行直接當成功；這個區分正確。

**Finding — 兩個診斷欄位應追加解釋，避免後續錯用**

1. `jacobian-observations.jsonl` 的 **`predicted_delta` 實際保存 `-J.T @ residual`**。它是未經阻尼矩陣求解的負梯度量，不是最終控制步；v004 還會再經半空間投影。若後續據此重播或解釋步幅，會使用錯誤量。保留原紀錄，追加欄位意義更正即可；未來實作應分別保存梯度、未約束步與實際約束步。

2. v004 的 **`max_halfspace_violation_m` 同時包含距離代理列和正規化控制 box 列**，全部殘差不能一律稱為公尺。現有資料可表示「混合約束的最大殘差」，不能拿它當最大物理穿入量；實際穿入仍應引用完整 contact report。未來應將兩類殘差及容差分開。這不推翻本輪完整 proposal 的碰撞讀回，也不構成重新搜尋的理由。

**Uncertainty／Risk／下一提案**

[next-method-proposal.json](C:/Repos/mmo-asset-pipeline/tmp/art-quality-loop/runs/qa/ro-swordsman-combo-r009/next-method-proposal.json) 明示 `draft_not_executed`、需要新 phase、不重置舊帳，且未自動搬骨或生成，範圍合理。建議保留兩項限定：

- `Root vector defect repaired underfixedgeometry` 應讀作**受測同姿勢的掌根權重缺陷已有改善**，不能外推為所有掌根姿勢已修復。v001 的改善可重用，完整形體與握持仍未通過。
- 審查 pad 覆蓋、法線與預期指節接觸是合理診斷；**不能把換一組較近的 pad 當成修好握持**。若新證據證明舊語義遮罩錯誤，應另存更正依據並同時保留舊門檻結果。Artist-authored targets 只能引導控制；pose corrective 則是新的形變製作，須有受限範圍與過程驗收，不能只把指腹投到劍柄後宣稱成功。

共面／相切／鄰接折疊、有限 inside 樣本、局部碰撞線性化與未測動畫的限制已清楚披露。16 跨 UV 島面、握持 interval、左手／衣甲、300 幀／60 fps、獨立 VFX 和新動畫 GLB 仍未通過或未執行。

122 tests 與 39 筆 schema 是主控的驗證紀錄，本審查沒有重跑；也未預先宣稱正在製作的 `final-verification.json` 已通過。

**停下與下一步**

主控可完成最終檔案驗證與上述診斷欄位的追加說明後，交付這批 **NO-SHIP 原型、可重用局部改善與失敗證據**供使用者檢查。r009 維持 4/4 closed，不新增候選；下一提案仍待使用者選擇，commit／push 保持 held。

本次審查已完成，目前沒有背景工作繼續執行。
