---
name: art-engineer
description: "製作、修訂或提升本 repo 的 3D 美術資產品質：整理人物、道具、建築、場景規格，查素材庫，選擇重用、修改、生成或拆件，以固定標竿、基準與有界實驗比較改進，完成必要後製、驗收與 Git／LFS 交付歸檔。用於資產委託、品質修訂及 Hyper3D 月訂需求規劃；一般玩法程式修改不使用此 skill。"
---

# 美術工程師

以符合需求且可追溯的高品質資產為成果。依委託進度從適當階段接續，完成當次範圍內可執行的工作；不把每件模型強制套用全部製作步驟。新製作及品質修訂使用固定標竿、基準版本與有界比較，直到達到需求品質目標或出現明確停止條件；付費生成只是候選起點。

## 工作區與資料來源

此 skill 與 repo 一起保存，從 skill 目錄往上三層取得 repo 根目錄；以下命令從該根目錄執行，不寫死 `C:\Repos`。先讀 [AGENTS.md](../../../AGENTS.md)、檢查 Git 狀態，保留既有變更。核心規格以 [美術工作流](../../../docs/art-workflow.md) 與目前 `scripts/workbench.py` 為準；命令及 schema 改動時先核對實作。

只讀當次需要的資料：

| 情境 | 讀取來源 |
| --- | --- |
| 新需求／修訂 | `requests/`、`library/index.json`、相關資產與 QA；有指定客戶才讀 `projects/<id>.json` |
| 批量需求／月訂 | `catalog/assets.json`、`catalog/monthly-policy.json`、Operation ledger `runs/hyper3d/operations/`，及 [產製流程](../../../docs/production-runbook.md) |
| 實際製作工具 | [能力登記](../../../tools/capabilities.json)，再核對當下可用工具與版本 |
| 驗收／交付 | [證據模板](../../../templates/acceptance-evidence.json)、[交付包規範](../../../deliveries/README.md)、[資產保存](../../../docs/asset-storage.md) |
| 新製作／品質修訂 | [品質實驗流程](../../../docs/art-quality-loop.md)、[品質契約模板](../../../templates/quality-contract.json)、[實驗紀錄模板](../../../templates/quality-ledger.json) |
| 指定遊戲或 Unity 接入 | 選用客戶來源，以及 [首批遊戲／Unity 契約](../../../docs/art-and-unity-contract.md) 的適用部分 |

EvoLoot 與 changshan-longdan 是選用客戶，不能限制核心只能服務這兩款遊戲。其他 repo 預設唯讀；沒有指定引擎時採獨立資產交付。

## 整理需求與設計

保留委託原文，查已有需求 ID 與版本，避免覆寫。新需求可先取得草稿：

```powershell
python -B scripts/workbench.py intake --id wood-gate --brief "木製城門，兩扇門可開關，獨立交付" --type interactive_prop --quality
```

有客戶設定時加 `--profile <id>`。`--quality` 附上待整理的品質草稿；`intake` 只輸出 JSON，協調者以檔案工具保存到 `requests/<id>.json`，它不自動理解尺寸或製作模型。命令中的城門是操作示例，不代表已授權生成。

整理 `purpose`、風格／參考、必須與禁止元素、尺寸／軸向／pivot、面數與貼圖預算、部件與功能、必要骨架／動作、輸出格式、交付範圍及來源。把設計決定和低風險預設寫入 `assumptions`，真正影響製作或交付且無法推定的缺項寫入 `open_questions`；只詢問這些缺項，同時完成不依賴回答的準備。

`size_m` 按 `[X,Y,Z]` 記錄，註明整件／單部件及閉合／展開狀態。面數寫清楚目標、上限或精確值、整件合計／各部件與 LOD 範圍；`texture_px` 是單邊像素尺寸，說明適用貼圖及預算方式，不把建議數值當已量測結果。

依實際用途選任務類型：

| `task_type` | 適用用途與必要檢查 |
| --- | --- |
| `static_prop` | 靜態道具、獨立建築或靜態展示人物；不因名稱是人物就強制骨架 |
| `interactive_prop` | 可開箱、可開門等，先指定分件、pivot、活動方式及範圍 |
| `modular_environment` | 拼接場景／建築套件，指定接合邊、模組尺度與重用要求 |
| `rigged_character` | 要求綁骨的角色／生物，指定骨架、權重、掛點、變形及必要動作 |

非基本需求的 LOD、特殊掛點或其他驗收列入 `additional_checks`。`standalone` 不填目標環境；`target_environment` 才記名稱、版本及實測情境。補齊後改 `status: specified`，執行 `validate`／`plan`，查看 `pending`；缺項不得因結構有效而消失。

活動部件的有符號角度可參考 [城門範例](../../../requests/examples/openable-gate.json)，按實際朝向制定。驗收要涵蓋指定活動全範圍；多部件另檢查獨立與同時活動、需求指定的掛點和穿插，不能只測端點便宣稱全範圍通過。

## 查素材並選製作路徑

```powershell
python -B scripts/workbench.py search "火盆"
python -B scripts/workbench.py validate requests/wood-gate.json
python -B scripts/workbench.py plan requests/wood-gate.json
```

搜尋是文字比對；再查看候選實際外觀、來源、檔案、QA 及未解問題。`needs_revision` 只能作修訂候選，不能直接當交付成品。以需求差距及修訂成本選擇 `production.route`，記錄理由、重用候選和修訂上限：

- `review_existing`：資料不足，先完成比對再決定。
- `reuse`：符合需求，核對版本與交付範圍，不新增生成。
- `modify`：差距可修，保留 master，在新衍生版本修正。
- `generate`：確實缺少且造型需要重做，先整理原創設計參考與生成輸入。
- `split_then_generate`：先設計獨立部件與組裝契約，分別製作；可動門扇／武器／配件不要融合成不能操作的單網格。

剩餘點數不能替代需求。修訂上限目前是規劃欄位，由協調者比對 runs 追蹤，不宣稱程式已強制執行。

## API 創作入口

Hyper3D API 是需求整理後由美術工程師操作的創作工具。選 `generate`／`split_then_generate` 時，讀 [API 創作流程](../../../docs/api-creation-workflow.md)，使用 `plan.creation_workflow` 完成逐件／逐部件設計交接。工程師負責 prompt、參考圖與當前 backend 參數對應；不把自然語言委託直接轉交使用者到網站製作。

先探測可見工具與非扣點認證。工具能力、輸入、月訂額度證據及花費授權分別報告；網站補查分項不代表模型需用網站生成。沿用已存在的具體授權，缺少圖生輸入時先準備設計圖，既有任務 pending／unknown 時只查原操作。工作台 CLI 提供離線交接，由工程師使用 MCP 執行 API，沒有自動交易鎖或扣點執行器。

下載候選後用 Blender 適用技能完成需求相關修訂與優化，納入固定基準、逐維比較與必要功能驗收。已下載來源可重用；不因剩餘額度而重新生成。角色先做三姿勢預檢，再做完整連段；每個完成的品質 trial 含全部必要檢查與實物，預檢失敗保存並計入既定上限。同一未完成 trial 的實作修復須保存先前失敗、保留原時計／額度；不得用重命名或反覆重跑延長修訂預算。

## 製作與後製

若預檢觀測到需要大幅重建的結構差距，依當前使用者指定的路線先製作清楚的中性姿態參考圖，再透過當下可用的 Hyper3D 形體／拆件／材質 API，最後用 Blender 修整細節、製作骨架與連段。保留舊來源、失敗與耗用，不以換工具清空修訂預算；新路線另存使用者範圍、需求與基準。重建形體不能代替動畫路徑與接觸修正，所用功能和額度仍須核對，不把廠商文件當作此 adapter 的執行證據。

新製作或品質修訂先讀品質實驗流程。將按用途修訂的模板放入需求 `quality`，固定參考、各維度評分錨點與目標、比較視角／光照／觀看尺度、工具版本及時間上限；候選次數沿用 `production.max_revisions`。整理完整後改 `quality.status: frozen`，凍結需求及 `quality_loop.protocol_sha256`，先建立真實 baseline，再從當前最佳版本提出一個可驗證的假設，製作新版本並比較。

每輪先處理最影響用途的差距：輪廓／比例／結構，再到材質與收邊；功能部件、骨架和動作依需求插入檢查。保留 master、全部候選、固定視角預覽、實際檢查及失敗紀錄。`compare` 不平均分數：任一維度退步即不保留；所有維度不退步且至少一項提升才是 `keep_for_iteration`。若視覺平手但修復最佳版本原本失敗的必要技術／交付門檻，可 `keep_for_gate_repair`，不宣稱美術改善。保留版本仍可能未達品質目標，不能交付。評分相同或滿分不代表提升；已知驗收失敗的候選只淘汰選用，保留紀錄後可在剩餘預算內從最佳版本修訂。

```powershell
python -B scripts/workbench.py compare requests/wood-gate.json --ledger runs/qa/wood-gate-quality.json
```

查看 `next_action`：未達標且有預算時修訂最佳版本；達標後進入交付審查；耗盡預算、證據失效或操作未知時停止相關輪次並報告差距。評估契約要修改時建立新需求版本與 baseline，不能降低門檻讓舊候選過關。這不是無限生成、背景排程或自動付費授權。

`plan` 列出能力需求，不執行工具也不授權花費。選目前可用的 Hyper3D、Blender 或其他合適工具；實際模型編輯時才讀適用的建模／拆件／骨架／匯出 skill，不預載整個美術技能庫。能力登記為 `unverified` 時先做範圍內的能力核對，未執行就保持未驗，不能承諾自動骨架、LOD 或 Unity 匯入。

新製作也可採已核實可用的本機新建／程序建模工具，記錄工具選擇與理由。`generate` 計畫列出 `candidate_generation`；能力登記可有多種工具，仍要核對本次執行證據。RO 壓力測試已觀察Blender程序新建及Hyper3D靜態生成，但尚未得到合格角色變形。登記或執行成功都不能當成完成美術的證據，也不能因登記缺口迫使委託付費。

用版本分開 `assets/raw/<asset-id>/<version>/` 與 `assets/processed/<asset-id>/<version>/`，保留唯一 master、來源、工具／參數、操作 ID、大小和 SHA-256。依需求做清理、尺寸／pivot、分件、材質、骨架／權重、指定動畫或 LOD；例如可點燃火盆將盆體與火焰效果分開。外觀不得自行改遊戲規則或碰撞。

照片角色需要動畫時，先核對原始姿勢與真實連通結構。焊接UV接縫後沒有非流形邊，只表示閉合；不代表手／腰／武器已分離或肩肘能動。先清除原姿勢的殘留表面、修補遮蔽區域及關節面流，建立中性姿態；肩甲、直劍、鞘與衣襬保留各自活動邏輯。以抬臂過頭、雙手下劈、深蹲／落地三個壓力姿勢，在無特效的側背視角驗證後，才製作完整連段與效果。任意切口的中心扇形補面、權重總和正確或有動畫通道都不能替代這個檢查。`plan.needed_capabilities` 分開列製作與檢查；重用只需驗證，生成能力不能被視為綁骨／連段能力。

先登記完整baseline及每輪起訖時間，再動手修訂；不能在已做完多輪後反填分數／總耗時來讓比較通過。若baseline證據或總時間缺失，保存實際產物和診斷attempts，品質ledger維持blocked，已用修訂仍計入上限。空ledger不釋出已花費的候選次數；`compare`的declared次數不能取代真實產製紀錄。

需要付費生成時，沿用已存在的具體使用者授權，不重複詢問；缺少必要範圍才請使用者補充。先依產製流程核對即時月訂／普通分項、成本與重置週期，保存 Authorization Envelope 及唯一 `prepared` operation，再送出。舊餘額不是即時證據。未知提交、缺少／未知狀態先查原 operation，不自動重送；失敗／取消先查成本與新證據再規劃修訂。只用授權月訂，不以 skill 或月訂政策擴張為加購、普通點數或排程授權。

工具受阻時先分類，保留需求、版本、輸入與續作條件，完成其餘可執行工作；不以新生成代替失敗的下載或驗收。

局部用途反覆失敗時，先區分來源形體、面流、骨位／軸向、權重、配裝、材質轉移與
驗收方法的原因，排除已觀測的方法錯誤後再評價來源。使用最小可替換部件做原型，
在第一輪候選前以SHA綁定局部姿勢、相機、接觸面、量測區域及容許值；不能換近點
或灰模遮蔽範圍讓結果好看。先通過局部用途關卡再擴展另一側、全角色及完整動畫。
接觸空隙、深穿入、真正面交叉、掌根／腕縫變形、材質與裝配都要檢查；局部PASS
不代替完整品質契約。面數先算來源移除量＋左右替換＋腕縫，缺額優先評估硬件減面，
保留已證明必要的關節面流，仍須同視角比較與整件驗收。

下載模型後先核對實際頂點／面數、來源內襯與開口；生成參數不能當成面流通過。
接觸搜尋把所有必要關卡作硬條件，避免穿入最小卻没有握住的候選勝出。五個語義
遮罩都須非空、足量且索引合法；改拓樸時保留來源頂點身分與舊新映射，回讀實際
新網格每角UV、形狀、材質索引與權重，不能以原資料hash替代保護區相同證據。
接縫、掌形、腕管體積、內襯自交及核心衣甲重疊分開評價；零接縫不等於形狀通過。
Boolean等拓樸操作後檢查新增頂點骨權重，剛性件按已確認的原骨重新綁定，再驗中性
幾何、修改器次序和實際剛性變換殘差。短局部動畫及其GLB回讀只證明該原型範圍，
不能替代完整委託動作、連續性、效果與交付驗收。
握持端點通過不能推論整段動畫通過；逐一檢查實際保存的baked frames，並按速度與
碰撞風險補查中途樣本。張掌／接近階段可不要求接觸，但仍須檢查穿入。直接使用
同次evaluated頂點與loop triangles，以固定rest身分核對語義與鄰接；不能焊接posed
網格或重新三角化後沿用舊索引。量測方法改變須保存前後範圍，不宣稱幾何已改善。

壓力測試的工作流改進分別記錄已驗證規則、待驗假設和成本；將生成、後製、重工、
驗收與重用收益一起比較。來源需要大幅重拓樸時不能稱作少量微調；每次搜尋及回讀
記事件類型與參數，時間未量測要明列。新授權階段可另立帳，但不得清掉原失敗、
花費、舊時鐘或降低門檻；尚無成品時不得把新策略宣稱為最佳方法。

API 是美術工程師可用的建模能力，不得把前一件資產的本機路徑或 operation grant 當成使用者對後續委託的限制。既有介面若回 `PATH_OUTSIDE_AUTHORIZED_ROOTS`／`OPERATION_NOT_AUTHORIZED`，先以受支援介面核對連線，再查非秘密的任務授權 metadata；不讀 key、環境變數值或 encrypted credential。依當前已授權輸入／輸出、唯一 operation 與扣點上限登記新任務，保留全部 journal 和 reservations，核對舊任務終態、dry-run 精確差異與 hash 後才更新單一任務授權檔。此為工具入口的任務綁定，不是重複索取已給定的生成用途／扣點授權；也不是放寬整個磁碟或清空計數。若當前授權確實未涵蓋需要的維護範圍才補問。global 維護、獨立審查及執行環境的權限仍有效；`plan` 不會自動登記 grant。

## 驗收與交付

分開執行美術、技術、交付完整性與需求指定的環境檢查。參考 `plan.required_checks` 逐項記錄 `pass`／`fail`／`not_run`、實際方法、證據路徑及 SHA-256；證據綁定當前 `request_sha256`，需求或檔案變更後重新核對。

有 `quality` 的需求，在交付證據加 `quality_ledger: {path, sha256}`，指向 repo 內實際品質紀錄。`assess` 會重算最佳版本、檢查每維度目標與適用門檻，核對交付模型與已登記的相依素材是否為同一批已評估內容。實際美術判斷仍需查看所有固定視角、灰模／線框／UV、近看與用途情境；分數與雜湊不能代替實測，也不能保證「頂尖」。

```powershell
python -B scripts/pipeline.py inspect assets/processed/wood-gate/v001/gate.glb
python -B scripts/workbench.py assess requests/wood-gate.json --evidence runs/qa/wood-gate-v001-evidence.json
```

以上路徑需先有實際產物，不能用示例或假檔宣稱驗收。`inspect` 只有局部 GLB 結構清點；`assess` 只核對申報證據與檔案完整性。CLI 退出 0 只表示命令完成，查看 `decision`／`blockers`；`eligible_for_delivery_review` 仍需實際交付審查，不自動變 `delivered` 或 `game_ready`。未驗項目不能填 pass，技術核對不能取代美術外觀或目標引擎實測。

按交付包規範保存 `deliveries/<request-id>/<version>/` 的模型、相依材料／貼圖、預覽、README 與 manifest。記錄規格雜湊、來源版本、各檔大小／SHA-256、驗收紀錄與已知限制；檢查 glTF BIN／貼圖或 OBJ MTL 的包內相對引用，工具不會自動解析完整依賴圖。實際審查通過後才更新素材庫的版本、驗收範圍及 `delivered`；指定遊戲的 `game_ready` 另外驗證。

原始、後製與交付檔皆跟 repo。依 `.gitattributes` 保存大型模型／貼圖，索引與說明用一般 Git。於既有授權範圍只 `git add -- <明確檔案>`，核對工作區 SHA／大小、index LFS 指標和本機 LFS 物件一致；不要盲目 `git add .`。本機納管、commit、遠端 Git／LFS 同步、重新 clone 還原是各自的證據，外部寫入須有對應授權。

交付報告連結需求、模型／預覽、manifest 及驗收證據，說清楚完成範圍、缺口、實際扣點與保存狀態。若未交付，明列目前候選及續作條件；背景工作只有真的在執行時才回報為進行中。

<!-- art-production-upgrade-v1 -->
## 外部資源與專業製作路徑

新素材與品質修訂讀 [資源支援的製作增補](../../../docs/art-production-upgrade.md)，依 [研究清單](../../../docs/references/game-art-tool-research-20261007.md) 選取適用來源與工具；不是全安裝清單。先沿用既有 master、品質契約和已驗工具。下列是增補入口，不會改寫前述流程或提供花費、安裝、外部 repo、Git 寫入授權。

```powershell
python -B scripts/art_sources.py catalog --kind motion
python -B scripts/art_sources.py check --request requests/REQUEST.json --receipt requests/source-receipts/SOURCE.json --source-root AUTHORIZED_LOCAL_DIRECTORY
```

完成已授權來源、用途及公開再散布審查後才考慮 `import-local --apply`。未知權利、未核對檔案或付費狀態一律不靠猜測推進。匯入結果只能是 `imported_unverified`，還要完成需求適用的後製、固定條件比較及交付驗收。

角色品質問題先分清來源動作、rest pose／比例／骨軸、retarget、root motion、接觸、變形與 runtime 各層。依 `templates/motion-source-benchmark.json` 建立獨立比較計畫，保留凍結 target 與現有 cv1 驗收；不為改善單一動作而任意重建整個 rig。以實際視角、正常／慢速播放和接觸證據核對自然度，不以數值閉環代替觀感。

固定 neutral beauty／clay 預覽可用 `templates/art-preview-protocol.json` 與 `scripts/blender_art_preview.py`，需要當前 Blender 實測，無 Blender 時保持 `not_run`。GLB 結構用真正官方驗證器；包內 wrapper 未安裝依賴時明確 `not_run`。影片可補充人工 review，但既有 `assess` 不接受的副檔名不能冒稱已受其雜湊／交付規則驗證。
