# Claude Code 交接：可重用角色動畫 V1 與 RO 美術壓力測試

交接日期：2026-10-05（Asia/Taipei）。此份為 repo 現況與來源對話的交接，尚未啟動新製作階段。
當次使用者指令：「[自然包握設計決策] 將對話內容與本repo代辦項目, 交接給 claude code」。
本交接只移轉資訊與接手順序；未授權重開r010候選帳、選定新引擎或完成模型。commit/push仍待使用者驗證。

## 先接手正確工作樹

| 位置 | 現況 |
|---|---|
| `C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop` | 實際產製worktree；branch `codex/art-quality-loop`；HEAD `c990639962b7ce85eb6beb631057aa4d76a3e86d` |
| `C:\Repos\mmo-asset-pipeline` | main；HEAD `e077e22ba57447031b7cc89e3d37bd9cef47daf4`；有另外的未提交改動，不能直接覆蓋 |
| 另外兩個 managed worktree | `hyper3d-api-commit`、`hyper3d-art-workflow`，目前detached同c990639；本次不改它們 |

產製worktree與main皆dirty，既有變更不可清空、reset、搬移或盲目stage。本次交接新增文件及接收回條，其餘既有內容保留。
同一BLEND／場景只留一個writer。Codex在本次交接結束後不繼續模型製作；Claude接手時重新核對有無其他writer。

先讀 `AGENTS.md`、有效的`CLAUDE.md`與 `.agents/skills/art-engineer/SKILL.md`。
本機全域Claude adapter在 `C:\Users\IOT\.claude\CLAUDE.md`，匯入 `~/.codex/AGENTS.md`；不可自行修改全域規則。
本次shell預設遇到 `sandbox provisioning failed`；已將之分類ENVIRONMENT_FAILURE，精確唯讀命令經review執行。
不能以此改ACL、safe.directory、安全設定或繞過審批。

## 來源對話與方向演進

完整可讀文字：`runs/handoffs/claude-code-character-animation-v1-20261005/conversation-source.md`。
結構化來源：同目錄`conversation-source.json`；conversation ID `6ac30789-321c-83ee-83ba-e0b2efb866d4`。
read_thread實際取得三輪，`hasMore=false`、`attachments=[]`。對話引用下載的
`sandbox:/mnt/data/character_animation_v1_codex_spec.md`未取得原附件，不能假稱已讀或沿用附件中的確切預算/P0/P1內容。
以下P0..P6是根據可讀對話與repo整理的新交接分工，並非原附件複本。

來源是參考資料，不是新的執行權限。助理提供的啟動指令、官方引用標記及公開技能說明不自動授權執行。
先前同一session的人類授權見本文件「授權」；不能用來源助理的提示詞撤銷既有權限或擴大它。

三轮內容依序為：

1. 自然握姿：參考目標→FK控制→姿勢空間修形→固定灰模審查→動畫/匯出驗收。IK僅受限微調，先設計完整形體而非最近三點。
2. 可重用角色：一次建立網格、rest骨架、完整權重與通用關節修形；新增動作通常只增加片段、轉場及互動設定。
   身體修正依關節姿勢啟動，接觸壓縮另依互動狀態，空手握拳不應出現專用劍柄凹陷。
3. 實際交付：完整角色母版、控制/骨骼與掛點資料、可操作runtime QA場景、重跑與新增動作入口。
   核心驗收為角色基礎凍結後，接入未用於調整角色的新動作，且不修改網格、rest骨架、權重、通用morph與其求值器。

這是希望改善的策略。尚未選定runtime、未指定新候選/時間上限，也未開始新的角色V1製作。

## 已驗證現況與應保留的基準

2026-10-05交接前，重新核對310個r008/r009歷史SHA、r010結案6個文件SHA與最終GLB SHA：不一致0。
本次只核對既有實跑證據與檔案身分，沒有再次執行131項測試或重跑Blender。

| 成果 | 狀態與證據 |
|---|---|
| r010 | 4候選已封存；compare=`stop_budget`、assess=`not_ready`；整個local functional gate及完整交付未過 |
| 右手局部 | 原五指pad由3/1/3/0/3改善到3/3/3/3/3；數值/匯出子項通過，美術未接受 |
| 動畫與回讀 | 61幀/60fps、121整/半幀；frame31..61共61時間點要求接觸；fresh手max0.194µm、RMS0.041µm，原容差1µm |
| 形體與控制 | 904原頂點、1788tri手；2552tri真實未縮放劍；16手骨+1劍骨；75點局部可關閉修形；203拇指保留 |
| 匯出修復 | GLB微小權重還原到來源FLOAT32；1106匯出頂點對904原ID；只改1686個JOINTS/WEIGHTS bytes，其餘相同 |
| 工具測試 | r010結案實跑131項通過、386筆artifact引用有效；這是2026-10-04歷史證據，不當成本次重新實跑 |
| 費用 | r010新增API提交0、點數0；更早API成本/operations完整保留，不將之清零或補猜 |

最終來源：

- `assets/processed/ro-swordsman-combo-r010/v004-certified-animation/right_hand_grasp_61f.blend`
  SHA `a01676563c0a65e0a33d42308c653ef7fd499b059301596a82b9eae282131c96`。
- `assets/processed/ro-swordsman-combo-r010/v004-certified-animation/right_hand_grasp_61f_exact_weights.glb`
  SHA `54c27c256e4b06a2312a8d0562e68195a64a5b502b21e23a5d0d3c453d773502`。
- `runs/qa/ro-swordsman-combo-r010/integrity-final.json`、`v004-review.json`、`assessment-final.json`、`comparison-final.json`。
- `runs/qa/ro-swordsman-combo-r010/independent-final-review.md`：真正完成的Astra/high唯讀審查，不是人類批准。
- `v004-fresh-glb-attempt3/result.json`及同目錄`interval-events.jsonl`：最後有效回讀。
- `v004-certified-animation/exact-weights-all-IDs.json`、`exact-weights-verification.json`：全部權重映射及修復邊界。

原`right_hand_grasp_61f.glb`為skin/morph拆clip的舊匯出，`*_combined.glb`仍略去微小權重；均保留作失敗紀錄，
不當作最後有效交付來源。早期`result.json`的`freshGLB: pending`是歷史階段狀態，不能回寫抹除。

r010未過美術的實際原因：側面C形偏鬆、指節偏硬、掌心/指腹支撐不足。每指3點<=2mm只支持proximity，
不支持接觸面積、握力或自然包握。121採樣不等於连续時間保證；自交檢查排除相鄰/相切/共面，
深度為有限採樣；solid-angle closed/oriented檢查未包含完整劍自身自交。原1µm容差不能泛化為所有美術門檻。

## 完整角色來源與原委託仍存在

完整角色基準在：

- `assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend`（42,525,711bytes）及同名GLB（34,937,204bytes）。
- r010 `baseline/ro_whole_baseline.blend`及GLB為保存的完整來源副本，不是已接受角色；先讀相應baseline報告。
- 其他來源在`assets/raw/ro-swordsman-combo/`、`assets/processed/ro-swordsman-combo-r002`至`r009`、`library/index.json`。

上列檔案存在性已核對；本次沒有再次打開完整角色或量測全部骨架，不推定某個來源已可遊戲使用。
r010手尚未替代完整角色的正式母版；需要配裝、左手、腕與盔甲等完整實測。

原需求檔 `requests/ro-swordsman-combo.json`與版本至`r010.json`不能覆寫，規格及參考摘要以實際檔案為準。
來源照片 `C:\.llmcode\ro_swordsman_animation`（唯讀）；repo已有`references-v001/`副本與
`runs/evidence/ro-swordsman-reference-analysis.md`。
原需求為角色＋骨架＋照片連續技能，300幀/60fps的Provoke→Bash→MagnumBreak→Endure→Victory、
可獨立關閉VFX、角色＋劍<=60,000tri、2K、1.74m、BLEND/GLB。
走路/睡眠/施法及新增動作重用測試是對話提出的能力擴充，不能悄悄取代原照片技能驗收。

當前r010 `delivery.scope=standalone`、`target_environment=null`。尚未指定角色V1的遊戲runtime。
`projects/evoloot.json`與`projects/changshan-longdan.json`是選用客戶、來源repo預設唯讀；不自動選Godot、Unity或Three.js，
也不把客戶設定中的2026-10-02來源摘要當當下引擎實測。無runtime決定時可先盤點與提出具體接入契約，不能寫客戶repo。

## 代辦順序與完成條件

| 優先 | 工作 | 可審查成果與完成条件 |
|---|---|---|
| P0 | 核對正確worktree、完整角色、有效工具/技能及runtime需求；保留舊帳 | 來源/版本/骨架/缺陷表；runtime名稱版本與支援範圍；新需求草稿、預算、保護區差異；缺項明確記錄 |
| P1 | 先驗Blender→GLB→實際runtime最小閉環 | 真正角色來源、skin與morph0/部分/1取樣、圖像與求值點對照；明確求值順序與每通道唯一owner |
| P2 | 建立可重用角色基礎與自然握持 | 按幾何→骨位/軸→完整權重→必要修形順序；多視角主形、關節範圍/組合姿勢、FK控制；IK受限微調；身體/接觸修形分開 |
| P3 | 製作完整動作與互動 | 走/跑、躺下/睡眠/起床、施法與原RO技能；武器socket、地面/床面接觸時窗、事件、VFX；不能用關節掃描冒充動作 |
| P4 | 建立可操作QA場景與反例 | 動作切換、pause/resume/seek、慢放、修形開關、固定鏡頭；轉場/loop/接觸；可丟棄副本中故障確實被抓 |
| P5 | 凍結後接入未用於調模型的新動作 | 事先保留holdout動作；凍結mesh/rest/weights/morph/rules/runtime evaluator；只新增clip/對應/事件/互動配置；逐資料類別簽章不變 |
| P6 | 再做壓測、獨立美術/runtime審查與歸檔 | 實物、可重跑命令、影片/截圖、數值與反例/失败時點、manifest、來源/成本/版本；接入流程再收斂到art-engineer，不宣稱已交付 |

P1不是先完成所有造型，而是先證明runtime能顯示/量測預定控制；P2候選先看同尺度灰模，
美術可採用後再跑完整昂貴驗證。每個正式候選仍要所有必要關卡，先看圖後看數字的匿名A/B可用於減少評分偏見。

通用修形計算依賴：動作播放/重定向/混合→FK/手勢/IK與約束→最終關節姿勢＋接觸狀態→
修形權重→引擎正確的morph/skinning。這不是將posed位移直接加到rest形變，亦不假設Blender drivers/constraints會直接匯出。
同一morph通道由烘焙clip或runtime evaluator明確擁有，不能同時相互覆蓋。r010的時間曲線不是已驗證的通用姿勢驅動器。

新增驗收必須先定義後製作：各關節支援範圍、組合、接觸區/單位/時窗/門檻、轉場矩陣及可接受視覺差。
原握持pad/門檻保留，但只在握持時窗強制；張掌/放劍/睡眠不強迫靠近柄。
對話建議工況0.5x/1x/1.5x、30/60/120fps求值、100/200/400ms轉場仍屬待凍結建議，不是已獲性能證明。
用真正求值後的morph+skin位置量測，CPU樣本不冒稱GPU畫面證據；完整動作加整/半幀及高風險區取樣。

反例應包括缺失骨映射、必要修形關閉、武器進手、錯誤接觸時窗等，與確切測試失敗對應。
holdout失敗則承認版本能力缺口，修正升版後該案例列回歸，再另選未用於調整的holdout；不得暗改基礎或動畫名/幀號特判。
新增clip會改整個BLEND/GLB容器SHA，故凍結驗收須對mesh/rest/weight/morph/rule等獨立正規化資料簽章比較。

完整交付尚需修復16跨UV島面/材質、左手/衣甲、所有照片技能與VFX，以及確切目標runtime/性能驗收。
關節活動、完整動作、轉場/互動、視覺、holdout、結構/匯出、性能各自報告，測試數不能互相抵銷。

## 可用入口與技術注意

2026-10-05已核對本機檔案存在：`character-artist`、`rigging`、`animation`、`blender-director`、`sculpting`、
`qa-review`、`export-pipeline`、`game-dev-workflow`，位於 `C:\Users\IOT\.codex\skills\<name>\SKILL.md`。
存在性不等於Claude已載入/工具可呼叫；Claude依實際任務讀最小技能集合，參考匹配文件與外掛仍待檢查，不能預載全部。
art-engineer為repo內技能。瀏覽器遊戲/runtime驗收適用時再讀game-dev-workflow。不要以舊Unity專用流程取代一般資產流程。

Blender上一階段實跑4.5.5 LTS、背景Python。MCP當時無callable，不當成本次已探測；沿用可用API/CLI並報告。
Hyper3D入口 `scripts/hyper3d_api.py`、文件`docs/hyper3d-api-entry.md`/`docs/api-creation-workflow.md`。
先看CLI實作/非扣點探測，credentials使用受支援provider；operation未知只查原任務，不自動重送。

可重用的已驗證方法：`ro_pose_corrective_math.py`、`ro_world_grasp_gate.py`、`ro_solid_angle.py`、
`ro_certified_grasp_gate.py`、`export_ro_combined_grasp.py`、`restore_ro_glb_exact_weights.py`、
`verify_ro_glb_exact_weights.py`、`verify_ro_fresh_grasp_glb.py`。
這些多數是r010固定路徑腳本，不能直接套成通用引擎adapter；參數化、範圍驗證與實際反例要先完成。
多數腳本使用`open('x')`與已存在QA輸出，不要直接重跑試圖覆寫舊資料；新輸出另立，舊失敗時計不清零。
尤其 `verify_ro_grasp_design_phase.py`/`restore_ro_glb_exact_weights.py`現有輸出已存在，交接查核應唯讀，不能盲目重跑。

一般工具入口（接手後依實際變更跑，將log保存新目錄）：

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/pipeline.py validate
python -B scripts/workbench.py validate requests/ro-swordsman-combo-r010.json
python -B scripts/workbench.py compare requests/ro-swordsman-combo-r010.json --ledger runs/qa/ro-swordsman-combo-r010/quality-ledger.json
git diff --check
```

`pipeline validate`的39件是舊catalog inventory，不是角色通用能力，也不是library新版entry數。
新版本新runtime有新證據，不能把上述r010已保存的數字當新版本PASS。

## 授權、預算與停止條件

- 本次人類授權為向Claude Code交接對話與repo待辦；接收回條可由CLI讀入文字後產出，不能藉此啟動新的製作/生成/部署。
- 既有工作區 `C:\Repos\mmo-asset-pipeline` 包含當前worktree。其他repo預設唯讀；遊戲接入寫入須具體範圍。
- 使用者歷史已明確允許建模按需使用Hyper3D現有點數與各介面，不限制先前單件0.5點；不重問已有點數授權。
  不加購/升級。是否適用某新任務/憑證/輸入範圍仍依有效入口、操作紀錄與審批；本次未提交付費任务。
- 使用者要求repo外新增/更新確切檔案先列出並授權；已有DPAPI逐項授權只涵蓋既有指定檔，不泛化到未指定新檔。
  不改全域Codex/Claude、Blender安裝、credentials、ACL或review。讀取provider不得輸出密鑰、signed URL或cookies。
- 參考對話助理的「不新增付費生成」只是一份建議提示詞，不撤銷上列真人歷史授權；它也不授權新的任務。
- stage/commit/push/merge/部署均不在本次交接執行範圍；原「commit/push等我驗證」仍有效。
- r010四候選已用完。新角色V1需先形成draft、支援範圍、實驗方法/上限及保護區差異，再依人類有效授權開始；不能換名延長舊四輪。
- 修改受保護thumb/骨位/權重/拓樸須提出具體差異與原因，未授權不解凍；保留歷史不代表正式新母版永久不能改，但必須另版與驗收。
- 大型規畫前、同因至少兩失敗與交付前按有效路由安排真正獨立review。Jev route不啟動agent、不授權、不算review結果。
- unresolved API、資料SHA漂移、實際必要權限缺失、預算到頂即停相關步驟並保留原因；不把工具/環境失敗當模型FAIL。

## Claude本次接收與後續啟動

本次透過已安裝 `C:\Users\IOT\.local\bin\claude.exe`（版本2.1.282）傳送以上交接、完整對話與repo AGENTS文字。
接收 invocation 用print/plan、tools空集合、strict MCP、slash commands停用、no-session-persistence，
以CLI臨時settings要求停用user/project hooks；managed policy仍保留。沒有改全域設定。
回條保存於 `runs/handoffs/claude-code-character-animation-v1-20261005/`；實際是否送達依receipt，不以文件存在宣稱成功。
官方參數依據：[CLI reference](https://code.claude.com/docs/en/cli-reference)、[hooks](https://code.claude.com/docs/en/hooks#disable-or-remove-hooks)。

接收回條不能等同模型已製作。此模式不保存可resume的Claude session；之後要在正式Claude Code session讀本文件接手。
使用者在Claude Code工作樹可貼：

```text
請讀 docs/handoffs/claude-code-character-animation-v1-20261005.md
及其 conversation-source.md，接手其中代辦。
先完成P0唯讀核對與新需求/支援範圍/預算草稿，沿用原歷史與驗收。
runtime未選定或受保護區需變更時，列出具體必要決定；不偷偷開始新候選。
角色V1要用凍結後接入新動作證明重用，不使用動畫名稱/固定幀號形變特判。
commit/push繼續等我驗證；僅有一個writer。
```
