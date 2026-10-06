# 可重用角色動畫 V1：P0 核對報告

核對時間：2026-10-05 約 11:17–11:28（Asia/Taipei；UTC 約 03:17–03:28；起點以交接檔最後寫入時間 11:16 之後估計，未精確計時）。執行者：Claude Code（單一協調者／單一 writer）。
授權來源：使用者 2026-10-05 指令「先完成 P0 核對與新需求草稿；保留原驗收、歷史及單一 writer。r010 不得重開；commit／push 繼續等我驗證。」
本階段只做唯讀核對與草稿。沒有製作候選、沒有修改任何模型、沒有 API 提交、沒有 Git 變更。

標記：**VERIFIED**＝本次實際執行命令觀測；**INFERRED**＝由觀測推論；**UNVERIFIED**＝本次未驗。

## 1. 工作樹、writer 與歷史完整性（VERIFIED）

| 項目 | 結果 |
|---|---|
| 產製 worktree | `C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop`，branch `codex/art-quality-loop`，HEAD `c990639962b7ce85eb6beb631057aa4d76a3e86d`，與交接一致 |
| main | HEAD `e077e22ba57447031b7cc89e3d37bd9cef47daf4`，有未提交改動；本次未觸碰 |
| 其他兩個 managed worktree | detached `c990639`；本次未觸碰 |
| index | staged 路徑 0（核對前後皆 0） |
| 交接檔 | `handoff-verification.json` 所列 9 檔 SHA-256 全部一致 |
| r010 最終 BLEND／GLB | `a0167656…131c96`／`54c27c25…773502` 一致 |
| r010 `phase-start.json` 所列歷史檔 | 311 筆路徑＋SHA 重算：一致 311、不一致 0、缺檔 0 |
| r010 `integrity-final.json` 文件 | 6 筆一致；`local-contract.json` 3 筆一致 |
| r010 需求雜湊 | `validate` 重算 `e4b26cc8…3e4b`，與 `comparison-final.json` 相同 |
| 其他 writer | 最近 120 分鐘內 worktree 只有交接檔被寫入（最晚 11:16）。一個 Blender 4.5.5 GUI（PID 6668，11:08 啟動）開著，視窗標題為 `(Unsaved)`，未開啟 repo 內 BLEND。Codex app-server 程序存在，未觀測到寫入。|
| Blender 唯讀開檔後 | 兩個受檢 BLEND 的 SHA 檢查前後相同（背景模式、`--factory-startup --disable-autoexec`、不存檔）|

限制：writer 核對是時間點觀測，不是鎖。`(Unsaved)` 的 Blender GUI 之後若開啟並儲存 repo 內 BLEND，需重新核對。

## 2. 完整角色來源／版本／骨架（VERIFIED，除另註）

完整角色只有一份實體：r007 baseline 與 r010 `ro_whole_baseline` 是位元組相同的副本。

| 檔案 | bytes | SHA-256 |
|---|---|---|
| `assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend` 與 r010 `baseline/ro_whole_baseline.blend` | 42,525,711 | `e1b17ac13d8677ef4914995e3308b18e99fd22f694c7fd240c541e74701d178e` |
| 同名 `.glb`（兩處相同） | 34,937,204 | `027cf2501619b4262ea8b040618364d2e756e6a3f476e12ed827fff9fadd2985` |

既有評語：`runs/qa/ro-swordsman-combo-r007/baseline/review.json` 判 `NO_SHIP baseline`，六維度分數 3／3／2／3／1／0，`source_not_accepted_master: true`。它是來源，不是已接受母版。

### 2.1 完整角色（`ARM_RO_Swordsman`）

| 類別 | 實測 |
|---|---|
| 場景 | Blender 4.5.5 LTS、60fps、frame 1–61、公制 scale 1.0 |
| 網格 | 10 件蒙皮網格，GLB 合計 **57,039 tri**（上限 60,000，餘 2,961）|
| 各件 tri | core 14,423；coat 12,542；cuirass 10,734；pauldron L/R 各 4,308；bracer L 3,026／R 2,404；sword 2,552；glove.R 1,918；WristLoft.R 824 |
| 骨架 | 53 骨（52 deform＋root）；全部 QUATERNION；**無約束、無 IK、無控制骨、無 driver、無 NLA** |
| 軀幹 | pelvis→spine_01→spine_02→neck→head（脊椎 2 節）；無上臂／前臂 twist 骨 |
| 右手 | 拇指 **2 節**（thumb.R_01/02）、四指各 3 節；另有 sword、wrist_transition.R |
| 左手 | 拇指 2 節、四指各 **2 節**；無獨立手套件，屬 `SM_RO_core` |
| 權重 | 所有件：零權重頂點 0、>4 影響頂點 0、未正規化 0；core 最多 4 影響 |
| 硬甲綁定 | cuirass 100% spine_02；pauldron 各 1 骨；bracer 各 100% lower_arm；sword 100% sword 骨 |
| coat | 4 個群組（pelvis／coat.L／coat.R／tabard），最多 2 影響 |
| morph | glove.R：`GripContact_R`；WristLoft.R：`WristVolume_025/050/075/100`。全由時間曲線 action 驅動 |
| 動作 | 只有 `RO_WristGrip_Prototype_61f_*` 3 個 action（骨 530 fcurves＋morph 4＋1），61 幀／約 1.017 秒 |
| 貼圖 | 11 張 2048×2048 內嵌（3 組 diffuse／normal／metallic-roughness＋腕皮 2 張）|
| 尺寸 | core 高 1.74m（Blender Z）|

### 2.2 r010 右手原型（`ARM_RO_HandDiagnostic`）

| 類別 | 實測 |
|---|---|
| 網格 | 手 904 點／894 四邊形＝1,788 tri；劍 1,493 點／2,552 tri（無 UV）；合計 4,340 tri |
| 骨架 | 17 骨：hand＋四指各 3＋**拇指 3**＋sword；手局部座標，骨名無 `.R` 後綴 |
| 權重 | 零權重 0、最多 4 影響、正規化 |
| morph | `SK_RO_GraspPulp_Corrective`，由 `AN_RO_RightHand_GraspMorph` 時間曲線驅動（driver 0）|
| 材質 | 灰模材質 `r010CorrectiveGray`；GLB 內 images 0 |
| 邊界 | 手 18 條邊界邊（位置本次未判別）|

### 2.3 缺陷與差距表

| # | 觀測 | 影響 | 證據層級 |
|---|---|---|---|
| D1 | 完整角色右拇指 2 節；r010 右手拇指 3 節 | r010 右手不能直接接回完整骨架；需擴充 rest 骨架（保護區提案 A）| VERIFIED |
| D2 | 左手四指各 2 節、每節指骨權重頂點僅 19–42 點、hand.L 227 點，無獨立左手件 | 無法做握拳／張掌施法；需左手替換（提案 B）| VERIFIED 數量；「不足以變形」為 INFERRED |
| D3 | 完整角色的 glove.R（1,007 點）與 r010 右手（904 點）是不同網格、不同座標系與骨長 | 接回需剛性對位、新腕縫與 WristLoft 重做；r010 局部 PASS 不能轉移到完整角色 | VERIFIED 差異；工作量 INFERRED |
| D4 | 所有 morph 由時間曲線驅動，driver 0 | 沒有已驗證的姿勢驅動器；通道 owner 未定義 | VERIFIED |
| D5 | 無 twist／輔助骨、脊椎 2 節、硬甲單骨 | 前臂旋轉、肩抬舉、躺臥的變形風險；是否需加骨待 P2 實測（提案 C 暫不申請）| VERIFIED 結構；風險 UNVERIFIED |
| D6 | 無控制層／IK | FK 握姿設計與 IK 受限微調需新建控制層 | VERIFIED |
| D7 | 只有 61 幀腕握原型動作 | 300 幀照片連段、走／跑／躺／睡／起／施法全部未製作 | VERIFIED |
| D8 | 各件皆有邊界邊：core 39、coat 1,216、cuirass 1,666、pauldron 各 892、bracer 496／336、sword 422、glove.R 92、WristLoft 92 | 可能是未焊接接縫或開口；本次未判別成因 | 數量 VERIFIED；成因 UNVERIFIED |
| D9 | r010 右手 16 個跨 UV 島面、材質未轉移 | 材質關卡未過（沿用 r007／r010 紀錄）| 引用既有紀錄，本次未重測 |
| D10 | r010 包握美術未接受：側面 C 形偏鬆、指節偏硬、掌心／指腹支撐不足 | 握持美術仍為失敗項 | 引用 `independent-final-review.md`，本次未重審 |
| D11 | 三角預算餘 2,961 | 估算：右手換 r010 手 −130；左手 +1,788、左腕 loft 約 +824、移除 core 左手約 −537（r010 假設中的歷史估值）→ 約 58,984，餘約 1,016 | **估算**，非量測 |
| D12 | 核心前臂與護腕重疊、材質 sampler 警告（library `r006-v008` open_issues）| 配裝未解 | 引用既有紀錄，本次未重測 |

未做：沒有渲染新圖、沒有量測骨軸／roll、沒有擺姿測試、沒有打開 r002–r009 其他 BLEND。

## 3. 工具與技能（VERIFIED 存在性／可呼叫性）

| 項目 | 狀態 |
|---|---|
| Blender | `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`，4.5.5 LTS（hash 836beaaf597a）；背景 Python 本次實際可執行 |
| Python／Node | 3.12.7／v22.22.0 |
| repo 工具 | `workbench.py`（intake／validate／plan／assess／compare／search）、`pipeline.py validate`、`hyper3d_api.py` 存在 |
| 單元測試 | 本次重跑 **131 項 OK**（`p0-unit-tests.log`）|
| `pipeline.py validate` | exit 0（`p0-pipeline-validate.log`）；是舊 catalog 39 件 schema，不是角色能力證據 |
| Codex 技能檔 | `character-artist`、`rigging`、`animation`、`blender-director`、`sculpting`、`qa-review`、`export-pipeline`、`game-dev-workflow` 的 `SKILL.md` 皆存在於 `C:\Users\IOT\.codex\skills\`。本 session 的 Skill 工具清單不含它們；需要時以讀檔方式取用對應的最小集合，本次尚未讀內容 |
| repo 技能 | `.agents/skills/art-engineer/SKILL.md` 已讀 |
| Blender MCP／Hyper3D MCP | 本 session 工具清單中沒有；未探測。Hyper3D 本次無需求，未做任何連線或餘額查詢 |
| glTF Validator | 未檢查是否安裝 |
| GitHub MCP、Playwright MCP | 連線失敗（session 啟動時回報）；P0 不需要 |

## 4. runtime：名稱、版本與支援範圍

目前 `delivery.target_environment=null`，**尚未選定**。本機觀測：

| 候選 | 本機版本（VERIFIED）| 客戶現況（唯讀觀測）| 支援範圍與代價（INFERRED，P1 才實測）|
|---|---|---|---|
| A. Three.js | changshan-longdan `package.json` `three ^0.186.0`、lock 0.186.0；Vite ^8.3.0、TypeScript ~6.0.2。主 checkout 未安裝 node_modules | 主分支是程序／體素視覺；專用趙雲 GLB adapter 只在 e00 worktree | GLB 原生載入；有蒙皮＋morph 的 CPU 求值位置介面可供量測；瀏覽器 QA 場景可讓你在 Chrome 直接操作。需在本 repo 內下載 `three@0.186.0`（及選用的 Vite），這是下載動作，需你同意 |
| B. Godot | 本機 `godot` 4.7.2.stable；EvoLoot `godot_client/project.godot` features 4.7 | BattleScene 是 Node2D＋JPG，尚無 3D 消費端 | 已安裝，不需下載；骨架修改在動畫混合之後執行的節點模型符合求值順序；可 headless 量測。沒有現成 3D 客戶場景可對照 |
| C. Unity | `C:\Program Files\Unity\Hub\Editor\6000.6.4f1` | 2026-10-02 摘要：兩個主 repo 無 Unity 專案；changshan-longdan 有 `e02-unity-foundation` worktree，本次未檢視 | 需建專案並取得 glTF 匯入套件；成本最高；與「Unity 是未來方向」一致 |

建議 A，理由：它是目前唯一有實際 3D 蒙皮 GLB 消費端的客戶 runtime，量測介面與瀏覽器可視驗收都直接可用，且所有寫入留在本 repo。選 A 不等於 Godot／Unity 可用，求值器日後需各自重寫與重驗。
未選定前只能做盤點與契約草稿；不寫任何客戶 repo。

## 5. 新需求草稿

檔案：`requests/ro-swordsman-character-v1.json`（`status: draft`、`quality.status: draft`）。
`workbench.py validate`：`valid_request`，request_sha256 `f88bc20479a041558512e4ee5222a923b149b73a674bfa7507e96945dadcacc3`（草稿每次修改都會變）。

保留不變的原驗收：
- style、must_have／must_not_have 原項、1.74m、60,000 tri、2K、+Y／+Z、BLEND＋GLB、standalone。
- 原 300 幀／60fps 照片連段 `AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory` 及其 animation_contract 六欄。
- 原 `export-roundtrip`、`skill-effects` 檢查。
- 品質契約：protocol、29 個 reference_artifacts（SHA 重算 29／29 一致）、六維度、anchors、target=4，由 r010 原樣複製並以程式斷言相等；只有 `status` 改為 draft、`budget` 為提案值。

新增（皆為待凍結提案）：
- 動作：Idle／Walk／Run／LieDown／Sleep／GetUp／Cast＋1 個 holdout。
- 9 個新增檢查：握持時窗接觸、關節範圍、片段集合、轉場與互動、runtime 閉環、凍結後 holdout 重用、反例、性能報告、獨立動作美術審查。
- `support_envelope`（關節範圍、組合姿勢、接觸門檻）、`transition_matrix_draft`、`runtime_contract_draft`（求值順序與通道唯一 owner）。

### 5.1 預算提案（未授權，`production.max_revisions=0`）

| 項目 | 提案 | 依據 |
|---|---|---|
| 正式候選上限 | 4 | r007–r010 各階段慣例 |
| 每候選／階段時間 | 6h／48h | 同上 |
| P1 閉環準備 | 上限 4h，不計候選 | P1 只證明接線，不是角色候選 |
| holdout | 每凍結版本 1 個；失敗則升版計 1 候選、原案例轉回歸、另選新 holdout | 交接文件 |
| 新 API 提交 | 預設 0 | 左手優先鏡射既有右手來源 |

`max_revisions` 設 0 是保守預設：草稿在你核准前，工具層面沒有可用的候選次數。

### 5.2 保護區差異

預設維持凍結：r010 右手 904 點 Basis／每角 UV／權重／16 骨位／203 拇指點／拓樸；原五指 pad（31／44／54／40／77 點）與每指 ≥3 點 ≤2mm 門檻；r008–r010 全部歷史與時計；六維度與 target；真實劍尺寸。

| 編號 | 變更 | 狀態 | 理由 |
|---|---|---|---|
| A | 完整角色 rest 骨架 53→59：新增 thumb.R_03、thumb.L_03、finger1–4.L_03 | 需你授權 | D1、D2 |
| B | 左手以 r007 右手來源鏡射替換，移除 core 既有左手面，新建左腕接縫 | 需你授權 | D2 |
| C | twist／輔助骨 | 暫不申請 | 待 P2 關節範圍實測提出證據 |
| D | 解凍 r010 右手 Basis／權重／拇指點 | 暫不申請 | 先以新增姿勢空間 shape key 處理 D10；不足時再提具體差異 |

## 6. 缺項（需你決定，草稿 `open_questions` 同步）

1. runtime 選 A／B／C。
2. 預算提案是否同意。
3. 保護區 A、B 是否授權。
4. holdout 動作由你指定並封存，或由我列候選、你抽選。
5. 睡眠床面規格（未指定時預設 0.45m 高、2.0×0.9m 代理）。

另：來源對話引用的 `character_animation_v1_codex_spec.md` 未取得。若你手上有該檔，放入 repo 後我會比對差異；沒有則以本草稿為準。

## 7. 本次檢查與範圍

執行並通過：HEAD／index 核對；交接 9 檔、r010 311＋6＋3 筆與 2 個最終檔 SHA 重算；GLB JSON 區塊清點；Blender 背景唯讀盤點 2 個 BLEND；單元測試 131 項；`pipeline.py validate`；新舊需求 `validate`；`plan`；`git diff --check`（exit 0，僅既有 CRLF 警告）。

未執行：任何模型修改、渲染、擺姿、GLB 匯出、runtime 載入、Hyper3D 連線／餘額／提交、LFS 檢查、Git add／commit／push、客戶 repo 寫入、獨立審查。P1–P6 全部未開始。

repo 外：只在本 session 的系統暫存目錄建立過 4 個工作檔（盤點腳本、其 2 個 JSON 輸出、一次性雜湊重算腳本）。前三者已複製到本目錄，4 檔皆已刪除；沒有其他 repo 外寫入。客戶 repo 只讀 `package.json`、`package-lock.json`、`project.godot` 的版本欄位。

本目錄檔案：

| 檔案 | 內容 |
|---|---|
| `p0-verification.md` | 本報告 |
| `p0-whole-baseline-inspect.json` | 完整角色 BLEND 盤點（物件、骨、權重統計、morph、action、貼圖）|
| `p0-r010-hand-inspect.json` | r010 右手 BLEND 盤點 |
| `p0-inspect-blend-used.py` | 實際使用的唯讀盤點腳本 |
| `p0-unit-tests.log`、`p0-pipeline-validate.log`、`p0-request-validate.json` | 本次實跑輸出 |
| `p0-snapshot.json` | 本次新增檔案與受檢來源的 SHA-256 |

盤點 JSON 內 `is_dirty_after_inspect: true` 是腳本在記憶體中計算三角形造成，檔案未儲存；SHA 前後相同已另行確認。
