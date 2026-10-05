# RO 劍士 r006：API 與局部握持壓力測試

**本階段已關閉：一次 API 生成、下載、8 次 Blender 修訂及局部 GLB 動畫回讀完成；完整角色仍為 NO-SHIP。**

比較結果為 `stop_budget`、`quality_target_met:false`，需求證據核對為 `not_ready`。
原需求的 300 幀／60fps 連續技能、左手、獨立可關閉 VFX 與完整交付驗收仍未完成。
沒有 staging、commit 或 push；目前沒有本任務 API、Blender 或覆核背景工作繼續執行。
[準備時 README](README-prepared.md) 與 [準備時學習紀錄](workflow-learning-prepared.json) 留作歷史，
其中「尚未生成／待授權」已由本頁、當次授權及 operation journal 的完成紀錄取代。

## 可直接檢查

- [右手設計圖](../../../assets/raw/ro-swordsman-combo/design-v006/right-glove-open.png)、
  [生成原始 GLB](../../../assets/raw/ro-swordsman-combo/rodin-v006/right-glove/base_basic_pbr.glb)。
- [最新 BLEND](../../../assets/processed/ro-swordsman-combo-r006/v008-rigid-wrist/ro_wrist_grip_prototype.blend)
  與 [最新 GLB](../../../assets/processed/ro-swordsman-combo-r006/v008-rigid-wrist/ro_wrist_grip_prototype.glb)：
  失敗診斷原型，內含 61 幀／60fps 張掌到握持動畫；不能當完成的技能交付包。
- [全角色三分之四視角](v008-rigid-wrist/whole-open/three-quarter.png)、
  [握持側面](v008-rigid-wrist/transition-1/side.png)、
  [GLB 匯入後第 61 幀](v008-glb-roundtrip/frame-061/side.png)。
- [最終判定](final-review.json)、[品質帳](quality-ledger.json)、
  [比較結果](comparison-final.json)、[需求核對](assessment-final.json)、
  [獨立覆核與量測限制](v008-independent-review.json)、
  [失敗分類](failure-classification.json)、[最後完整性與工具驗證](final-verification.json)。

## VERIFIED：本次 API 與授權

入口完整路徑為 `C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py`。
在 repo 執行 `python -B scripts/hyper3d_api.py --help`；使用方式見
[API 入口文件](../../../docs/hyper3d-api-entry.md)，創作規則見
[API 創作工作流](../../../docs/api-creation-workflow.md)。

使用者授權的確切任務檔
`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-hand-source-20261003-001.dpapi`
已建立，934 bytes；由既有受支援的 Windows DPAPI provider 保存與恢復本筆任務查詢識別，
不含 API 主密鑰，不把明文識別寫入 repo。恢復綁定與檔案雜湊已核對。
舊 `authorization.json` 與 `rodin_api.py` 雜湊不變；此處只聲明實際核對過的檔案。

operation `ro-hand-source-20261003-001` 只付費提交一次，狀態 `downloaded`；
原 GLB、preview.webp、render.jpg 均已落地並保存 SHA。
服務回報本筆 **0.5 點**，不是用整數餘額差推估。
預檢與完成時回傳餘額皆為 228，未回傳月訂／普通分項；這是當時觀察，並非即時餘額聲明。
沿用既有按需月訂／普通點數授權，沒有另設 API 點數上限、加購或升級。
[API 完成驗證](api-completion-verification.json)、
[operation journal](../../hyper3d/operations/ro-hand-source-20261003-001.json) 保存詳情。

doctor 前後都是 18 ok／10 notes／6 warn／1 fail；既有失敗為
`elevated Windows sandbox provisioning recorded a structured failure`。
受影響命令經逐次完整命令審批執行；沒有修 ACL、關閉審批或改安全控制，也不宣稱全域環境通過。

## VERIFIED：8 次局部修訂

真正的中性與左右握持 baseline 先建立，29 張固定視角、58,868 tri／48 骨。
修正舊方法的指軸後，baseline 仍有右手約 7.05 mm 深穿入及左拇指約 23.68 mm 接觸距離。
原始來源幾何、UV、權重與 master 雜湊保留。
完整需求與固定局部關卡見 [需求](../../../requests/ro-swordsman-combo-r006.json)、
[hand-gate-contract.json](hand-gate-contract.json) 與 [baseline 綁定](baseline-binding.json)。

| 修訂 | 方法與實測結果 | 未通過項目 |
| --- | --- | --- |
| v001 | 接入生成手套與獨立指骨 | 9.84 mm 深穿入、359 劍柄交叉對；60,664 tri |
| v002 | 36 筆事件的角度／位置搜尋 | 穿入歸零但失去握持；四指無接觸，60,543 tri |
| v003 | 39 筆事件的獨立指關節 IK | 五指接觸達標，但 2.05 mm 穿入、54 交叉對 |
| v004 | 有界 3.804 mm 接觸形狀修正 | 劍柄穿入與交叉歸零；拇指接觸不足、腕袖失敗，60,699 tri |
| v005 | 拇指與腕部配裝修訂 | 指墊接觸 4／4／5／4／4；腕口膨脹、甲片穿插，60,543 tri |
| v006 | 診斷內外雙層腕口，建立有序雙層連接 | 接縫與手套／腕管對甲片交叉歸零；腕口膨脹、core／甲片穿插，60,386 tri |
| v007 | 調整被甲片覆蓋的前臂與甲片空腔 | 57,039 tri；Boolean 新增 265 個無權重頂點，動作時甲片破形 |
| v008 | 修復剛性甲片權重、腕管形狀及 61 幀局部原型 | 面數、局部握持與回讀通過；掌腕摺疊、自交診斷及 core／甲片穿插仍失敗 |

所有完整候選都記為 `failed`；帳面 current best 仍是原 baseline，而 baseline 本身也未達交付標準。
候選之間保留診斷原型鏈，不把局部成功提升為已接受的 master。

API 請求 Quad／target 1000，GLB 實測 2,268 tri、2K packed PBR、內外雙層腕口。
GLB 會三角化，這個數字不能證明服務的原生 Quad 生成失敗，也不能證明動畫面流可用。
切除後保護的 915 頂點／1,780 三角面，其 Basis、形狀修正、權重與 UV 已實際回讀相同。
所有五指語義遮罩在搜尋前固定；另做五個非法遮罩負面測試，均被拒絕。

v008 全角色與劍共 57,039 tri、53 骨；剛性甲片預測最大誤差 0.303 µm。
完全握持端點的指墊接觸為 4／4／5／4／4，該端點劍柄深穿入與橫向面交叉為零。
更正：不能把這個端點結果宣稱為五樣本或整段局部動畫的碰撞通過。
[追加的 baked clip 範圍更正](v008-baked-clip-scope-correction.json) 保留同一來源的重新播放結果：
frame 1／16／31／46 仍有約 7.19／5.43／3.41／1.34 mm 劍穿入，frame 61 才歸零。
原有模型、閉合品質帳、成本與 NO-SHIP／stop_budget 判定未改寫；端點接縫通過仍不能抵銷掌腕缺陷。
然而手套自交診斷對數為 0／0／175／335／491，腕管為 0／0／13／285／138，
core／護臂交叉對數為 170／167／165／173／211；實際近照仍見掌腕摺疊與腕口鼓起。

自交對數是診斷三角面配對數，不是獨立缺陷數；診斷重焊／三角化、頂點順序未明確斷言、
共享頂點與相切／共面排除均有限制。零不能證明完全無自交；正值與近照共同支援 NO-SHIP。
腕管最大 20.777 mm 修正、前臂最大 46.680 mm 配裝已屬大幅改形，不能描述為微調。

## VERIFIED：實際 GLB 局部動畫回讀

[新程序匯入結果](v008-glb-roundtrip/roundtrip.json)：
10 meshes、53 bones、1 skin、1 animation、161 channels、11 embedded images。
Blender 4.5.5 LTS 背景程序採 `--factory-startup --disable-autoexec`，
沒有呼叫 `read_factory_settings`，匯入關閉自動 bone-shape 建立。

原時間 1/60 至 61/60 秒保留，實際求值全部 61 幀骨架與形狀修正。
五個樣本、手套／腕管／護臂／core／劍的雙向頂點到曲面誤差均低於 0.1 mm，
最大約 **0.014141 mm**。GLB 確實播放局部動作，原本的失敗形狀也在匯入後重現。
這是一秒局部動畫的幾何回讀通過，原需求的 300 幀連段、左手、VFX 與全材質等價仍未驗收。
匯出警告 `More than one shader node tex image used for a texture` 尚未解除。

驗證器修正過錯誤的「時間必從零開始」、同名 EMPTY 與 skin 匯入重新掛父節點假設；
最後以原 GLB 的 named node.mesh 精確綁定實際 mesh data。三次失敗程式／log 與成功 log 都保留，
不以重生模型掩蓋驗證器問題。

## 工作流、成本與停止條件

已更新 [美術工作流](../../../docs/art-workflow.md)、
[品質實驗規則](../../../docs/art-quality-loop.md) 與
[art-engineer skill](../../../.agents/skills/art-engineer/SKILL.md)。
[工作流學習](workflow-learning.json) 保存實測與歷史假設，`best_workflow_proven:false`：
先固定用途、語義遮罩與保護區；接觸／穿插等必要關卡先於單一分數；
幾何修改後重驗骨資料；局部接縫或回讀成功不能抵銷外形與配裝失敗。

本階段在 baseline 前啟動，閉合時鐘 **10,887.310051 秒**，包含等待與候選 QA；
八次修訂的登記時數和相同，沒有重設時鐘或降低原品質要求。
本次 API 成本 0.5 點；r005 的三次失敗、14,607.710521 秒及 1.0 點保留，
r005＋r006 服務回報合計 1.5 點，只涵蓋這兩階段。
新設計圖工具耗時 19.6 秒另記，工具未回傳圖片金額，更早規劃時間未量測。
歸檔與最終工具檢查時間另見 final-verification，不覆寫已閉合時鐘。

下一個製作方法須先處理實際掌根／拇指對掌／腕部面流、骨位、權重與內襯，
並把舊 core 的整合盔甲體積另外診斷；現有證據不足以將失敗全部歸因於生成拓撲。
本 r006 修訂預算已用完，不再追加候選，也不從失敗原型擴展完整連段。
commit、push 保留，等待使用者驗證成果。
