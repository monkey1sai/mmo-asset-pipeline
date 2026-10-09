# 趙雲次級骨鏈相容性提案

Task：`secondary-rig-contract-proposal`，接續 S2 的實際缺骨發現。此 task 交付可審查方案及來源核對，不套用骨架、不修改遊戲、不新增角色候選。完整 SPEC 仍 **1/6、NOT_COMPLETED**。機器可讀提案：[zhaoyun-secondary-rig-extension-v1.json](proposals/zhaoyun-secondary-rig-extension-v1.json)，`execution_profile=false`。

## 已核對的現況與接入限制

遊戲來源 origin/main `e85840fad45b7704fab994945aee229f886c3b22`。本地讀取的 `ZhaoYunContract.cs`、`CharacterImportValidator.cs`、`SkinBinding.cs`、`src/view/zhaoyun-adapter.ts` 與該 ref 無內容差異；逐檔 SHA 保存於本地報告，沒有修改工作區。

- `unity/ChangshanLongdan/Assets/Character/Runtime/CharacterImportValidator.cs` 同時要求 imported joints 數量等於契約、順序 `SequenceEqual`。附加六骨後 27≠21，依來源分支預測回 `REQUIRED_BONE_MISSING`，即使所有原骨都在。這是 **INFERRED_REJECTION**，沒有執行 Unity C# 驗證器，不能寫成 Unity 實測 FAIL/PASS。
- `SkinBinding.cs` 與 Web adapter 每幀仍 bind/write `cape_01/02`。新 solver 同時寫它們會違反單一 writer 契約。
- `CharacterAnimation.Bind/Step` 從 `Skin.PlacedBones` 建立 Transform 對照及父先子後寫入。未加入此路徑的髮／飄帶鏈不能假定已由現有 driver 執行。
- `CharacterAnimation` 另有 glTFast X mirror 與 logic/display 轉換；既有 authoring preset 為 Z-up metres，不能直接照抄為 Unity Y-up 參數。body pose 的程序骨長 scale 也不能被既有 rigid-only 參考 solver 默認接受。

## 建議方案與保護範圍

建議由遊戲端確認新版契約後，**保留原 21 骨順序、索引、父鏈及 rest transforms，只附加最多六骨**。這是最小鏈 prototype 提案，不保證三段鏈已滿足馬尾全部分束的觀感；需要局部 DCC 審查與調參。

| 提案索引 | 新骨 | 父骨 | 用途 |
|---|---|---|---|
| 21–23 | hair_01 → hair_02 → hair_03 | 第一段接 head，其後接上一段 | 長馬尾；根部 offset／髮扣固定 |
| 24–26 | ribbon_01 → ribbon_02 → ribbon_03 | 第一段接 pelvis，其後接上一段 | 僅在確認獨立飄帶及繫點後採用，否則不建立此鏈並另定契約 |

掛點 offset、骨軸、rest length、碰撞代理半徑／位置尚未量測，提案保留 NOT_MEASURED，不用合成 fixture 數值冒充角色設定。Mixamo → 原 target 的身體映射沿用既有路徑；新增骨全部排除於 body animation channels。披風、裙甲、髮束、飄帶各有唯一 secondary writer；同一活動骨只能選 baked clip 或 runtime solver。

遊戲端影響明細：版本化 joint count/order 與候選 manifest，保留嚴格驗證；新骨加入明確 Transform 寫入路徑；接入次級求解時替換既有披風 writer；使用相同 simDt/simTime，hitstop/pause 凍結，瞬移／重生 reset 全鏈；驗證 inverse bind matrices、原 21 骨與動畫回讀；重跑完整 Unity 遊戲驗收。不能以放寬驗證器、忽略新增骨或讓 GLB 自帶 solver 取代接入。

武器保護：`SM_ZhaoYunSpear`、hand_l/r 握持、局部 tip Z=2.7、tipBase Z=1.25、最小 Z=-1.05 與玩法/root-motion policy 保持契約。骨鏈提案不授權重建或改尺寸。另一種獨立 renderer/附加骨架路線也需 mesh/契約/重複表面審查，不能聲稱可零改動繞過目前 21 骨限制。

## 已執行驗證與未放行項

本地 `runs/evidence/zhaoyun-chain-compat-v001.py` 唯讀核對實際 C# joint array 與提案原 21 骨完全相同、append-only 索引與父鏈有效、來源檔前後 hash 相同。直接採用現有 `scripts/rig_motion.py::validate_export_channels` 做三個 **合成** probe：17 個 body-only channel 合法；body/cape 同寫回 `BONE_WRITER_CONFLICT`；body clip 夾入 hair track 回 `EXPORT_UNOWNED_BONE_TRACK`。三者均符合預期，核心沒有另建 checker 或修改。

本地報告 `runs/qa/zhaoyun-chain-compat-v001/report.json` SHA-256：`d372c0d8da97d138e2a82daaac6a6c3187728d87e9a9ea3aa776fe41ede413c5`。它只證明來源規則與工程 ownership probes；**Unity 執行、真實新骨／配重、Mixamo 整合及遊戲接受全部 NOT_RUN**。S2 完整遮罩仍 NOT_ACCEPTED，兩個歷史候選 FAIL／舊餘額 0。

下一個必要決策是遊戲端是否接受這個 append-only 新版骨架契約方向；使用者原要求「若必須改 target rig，先提出骨架映射、相容性差異與接入影響，交由遊戲端確認」。本文件完成這項前置準備，沒有自行解除它。確認方案也不重設 S3 候選預算或批准 Mixamo 外傳。回滾為不採用提案、維持原 21 骨資產；沒有需要撤銷的遊戲修改。
