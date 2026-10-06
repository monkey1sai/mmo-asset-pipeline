# 獨立灰模 A/B 盲審（唯讀子代理回報，原文）

時間：2026-10-05。審查者：本 session 派出的唯讀子代理，只看 `../gray-review-ab/` 的 21 張圖，未取得 A/B 對照表。
受審對象：r4 baseline 與候選 v001 的 a34-hands 版本（b03-hands 幾何相同，另加手部貼圖）。這是模型產出的審查意見，不是人類批准。
解盲與處置見 `disposition.json`：審查者標為 [S] 的一方，在核對的 8 列中全部是候選。

---

## Scope／盲審聲明
- 只讀了 `C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop\runs\qa\ro-swordsman-character-v1\v001\a34-hands\gray-review-ab\` 內 21 張 PNG（全部用 Read 看過）。唯一的額外動作是用 Glob 列出該資料夾的 `*.png` 檔名；沒有開任何 JSON／log／key／report，沒有搜尋 repo。
- Evidence = 21 張圖的目視判斷（解析度約 320px/格，細節有限）。A/B 版本歸屬是依外觀推論，不是檔案證據。

## 圖例
t/e = typical/extreme；nv = 無可見缺陷；NP = could not be posed；? = 被遮住或太小無法判斷；同 = 與 A 相同；Y* = gameplay 距離可出貨、近拍不行。
RC = 胸甲像橡膠整片彎曲，腰帶裙甲不動。PH = 肩甲不跟手臂，留在原位懸在抬起的手臂下，腋下拉出細薄片。EC = 前臂甲切進肩甲，手肘塌陷。SW = 裙甲在大腿穿出處裂成暗色楔形缺口。KC = 小腿塌進大腿、靴子切裙襬。
[S] = 光滑型手（乾淨環狀袖口、劍斜握掌中、所有指關節可擺）；[L] = 粗糙型手（細而歪的手指、皺褶捲邊袖口、手腕硬接縫、劍橫握掌中）。

## 逐列表
| 檔案 | 動作 | 較佳 | A 最差缺陷 | B 最差缺陷 | A typ | B typ |
|---|---|---|---|---|---|---|
| ab-torso-01 | spine-flexion | = | t: 胸甲輕微橡膠折痕；e: RC | 同 | Y | Y |
| ab-torso-01 | spine-extension | = | t: nv；e: RC | 同 | Y | Y |
| ab-torso-01 | spine-lateral | = | t: nv；e: RC，受壓側胸甲下緣沉入腰帶 | 同 | Y | Y |
| ab-torso-01 | spine-twist | = | t: nv；e: 胸甲剪切、裙甲不動 | 同 | Y | Y |
| ab-head-01 | neck-yaw | = | t: nv；e: 下顎歪斜 | 同 | Y | Y |
| ab-head-01 | neck-pitch | = | t: nv；e: 下巴沉入護頸 | 同 | Y | Y |
| ab-head-01 | neck-roll | = | nv / nv | 同 | Y | Y |
| ab-arm-L-01 | shoulder-flexion.L | = | t: 肩甲下方暗縫；e: PH | 同 | Y | Y |
| ab-arm-L-01 | shoulder-extension.L | = | t: nv；e: 肩甲與軀幹間細薄片 | 同 | Y | Y |
| ab-arm-L-01 | shoulder-abduction.L | = | t: 腋下帶狀薄片；e: PH、肩部扁塌 | 同 | Y | Y |
| ab-arm-L-01 | shoulder-axial-plus.L | = | nv / nv | 同 | Y | Y |
| ab-arm-L-02 | shoulder-axial-minus.L | = | nv / nv | 同 | Y | Y |
| ab-arm-L-02 | elbow-flexion.L | = | t: nv；e: EC | 同 | Y | Y |
| ab-arm-L-02 | forearm-pronation.L | = | [L] t/e: 袖口皺褶堆擠、側視手指像黏住 | [S] nv / nv | Y | Y |
| ab-arm-L-02 | forearm-supination.L | B | [L] t: nv；e: 袖口皺褶扭轉 | [S] nv / nv | Y | Y |
| ab-hand-L-01 | wrist-flexion.L | B | [L] t: 手指細而歪；e: 手指壓扁成帶狀 | [S] t: nv；e: 手腕像橡皮管彎、掌底硬黑邊 | Y | Y |
| ab-hand-L-01 | wrist-extension.L | B | [L] t: nv；e: 手背腕部夾陷凹折、手掌壓扁 | [S] nv / nv | Y | Y |
| ab-hand-L-01 | wrist-radial.L | B | [L] t/e: 手腕橫向硬接縫、臂甲暗色裂縫 | [S] nv / nv（氣球般無細節） | Y* | Y |
| ab-hand-L-01 | wrist-ulnar.L | B | [L] t/e: 腕接縫、中間手指互疊 | [S] nv / nv | Y* | Y |
| ab-hand-L-02 | fingers-mcp-flexion.L | = | [S] t: 四指折成一片平板、指縫極淡；e: nv | [L] t: 拇指粗如香腸；e: 手指疊成薄板 | Y | Y |
| ab-hand-L-02 | fingers-pip-flexion.L | = | [S] t: nv；e: 折成硬角楔形、PIP 失體積 | [L] t: nv；e: 指尖互相穿插 | Y | Y |
| ab-hand-L-02 | fingers-dip-flexion.L | B | NP | [S] nv / nv | N | Y |
| ab-hand-L-02 | fingers-spread.L | B | [L] t: 指節凹凸、腕接縫；e: 幾乎沒再張開 | [S] nv / nv | Y* | Y |
| ab-hand-L-03 | thumb-cmc-opposition.L | A | [S] t: nv；e: 拇指根鼓成一坨 | [L] t: 虎口拉出尖刺；e: 尖刺更長 | Y | N |
| ab-hand-L-03 | thumb-mcp-flexion.L | A | [S] nv / nv | [L] t: nv；e: 外緣稜角 | Y | Y |
| ab-hand-L-03 | thumb-ip-flexion.L | A | [S] nv / nv | NP | Y | N |
| ab-combo-01 | combo-empty-fist.L | A | [S] t/e: 拳頭是鼓脹方塊、手指糊成一團 | NP | Y* | N |
| ab-combo-01 | combo-empty-fist.R | B | NP | [S] t/e: 指節糊成團塊 | N | Y* |
| ab-combo-01 | combo-arms-overhead | = | t: nv（太小）；e: 雙側 PH | 同 | Y | Y |
| ab-combo-01 | combo-two-hand-chop | = | 手太小；劍刃朝側向（握點方向） | 手太小；劍刃朝上 | ? | ? |
| ab-combo-02 | combo-deep-squat | = | t: nv；e: 裙甲被大腿頂成錐狀（太小） | 同 | Y | Y |
| ab-combo-02 | combo-cast-open-palm.L | = | t: nv；e: PH | 同 | Y | Y |
| ab-combo-02 | combo-grasp-wrist-flexion.R | A | [S] t: nv；e: 指節糊成團 | NP | Y | N |
| ab-combo-02 | combo-grasp-wrist-extension.R | B | NP | [S] t: nv；e: 手掌略壓扁 | N | Y |
| ab-combo-03 | combo-grasp-wrist-radial.R | B | NP | [S] nv / nv | N | Y |
| ab-combo-03 | combo-grasp-wrist-ulnar.R | B | NP | [S] nv / nv | N | Y |
| ab-leg-L-01 | hip-flexion.L | = | t: nv；e: SW | 同 | Y | Y |
| ab-leg-L-01 | hip-extension.L | = | nv / nv | 同 | Y | Y |
| ab-leg-L-01 | hip-abduction.L | = | t: nv；e: 裙甲側片隨大腿剪切拉伸 | 同 | Y | Y |
| ab-leg-L-01 | hip-axial-plus.L | = | nv / nv | 同 | Y | Y |
| ab-leg-L-02 | hip-axial-minus.L | = | nv / nv | 同 | Y | Y |
| ab-leg-L-02 | knee-flexion.L | = | t: nv；e: KC | 同 | Y | Y |
| ab-leg-L-02 | ankle-dorsiflexion.L | = | t: nv；e: 靴面折疊壓縮 | 同 | Y | Y |
| ab-leg-L-02 | ankle-plantarflexion.L | = | nv / nv | 同 | Y | Y |
| ab-leg-L-03 | toe-extension.L | = | 看不出腳趾動作（硬靴） | 同 | ? | ? |
| ab-arm-R-01 | shoulder-flexion.R | = | t: 肩甲下暗色帶狀尖刺；e: PH | 同 | Y | Y |
| ab-arm-R-01 | shoulder-extension.R | = | t: nv；e: 肩甲處薄片 | 同 | Y | Y |
| ab-arm-R-01 | shoulder-abduction.R | = | t: 腋下帶狀薄片；e: PH、上臂暗色拉伸線 | 同 | Y | Y |
| ab-arm-R-01 | shoulder-axial-plus.R | = | nv / nv | 同 | Y | Y |
| ab-arm-R-02 | shoulder-axial-minus.R | = | t: nv；e: 肩甲片間裂開暗縫 | 同 | Y | Y |
| ab-arm-R-02 | elbow-flexion.R | = | t: nv；e: EC | 同 | Y | Y |
| ab-arm-R-02 | forearm-pronation.R | = | [L] t/e: 臂甲下緣鋸齒、手指併攏 | [S] t/e: 臂甲下緣鋸齒 | Y | Y |
| ab-arm-R-02 | forearm-supination.R | B | [L] t: 側視手指糊成連指手套；e: 袖口環帶扭轉 | [S] nv / nv | Y | Y |
| ab-hand-R-01 | wrist-flexion.R | A | [S] t: nv；e: 橡皮管式彎曲 | [L] t: 袖口腫塊；e: 手掌壓成薄片 | Y | Y |
| ab-hand-R-01 | wrist-extension.R | B | [L] t: 手被劍遮住；e: 手背腕部夾陷 | [S] nv / nv | ? | Y |
| ab-hand-R-01 | wrist-radial.R | = | [L] nv / nv（僅袖口摺痕） | [S] nv / nv（掌部方正鼓脹） | Y | Y |
| ab-hand-R-01 | wrist-ulnar.R | = | [L] nv / nv | [S] nv / nv | Y | Y |
| ab-hand-R-02 | fingers-mcp-flexion.R | A | [S] t: 四指折成平板；e: nv | [L] 被護手遮住 | Y | ? |
| ab-hand-R-02 | fingers-pip-flexion.R | = | [S] t: nv；e: 硬角楔形 | [L] t: 半遮；e: 稜角雜亂、大半被遮 | Y | ? |
| ab-hand-R-02 | fingers-dip-flexion.R | = | [L] nv / nv | [S] nv / nv | Y | Y |
| ab-hand-R-02 | fingers-spread.R | B | [L] t: nv；e: 外側手指剪切成扁平碎片 | [S] nv / nv | Y | Y |
| ab-hand-R-03 | thumb-cmc-opposition.R | = | [L] t: nv；e: 拇指壓成團塊 | [S] nv / nv（拇指半被護手遮） | Y | Y |
| ab-hand-R-03 | thumb-mcp-flexion.R | = | [L] nv / nv | [S] nv / nv | Y | Y |
| ab-hand-R-03 | thumb-ip-flexion.R | B | NP | [S] nv / nv | N | Y |
| ab-leg-R-01 | hip-flexion.R | = | t: nv；e: SW | 同 | Y | Y |
| ab-leg-R-01 | hip-extension.R | = | nv / nv | 同 | Y | Y |
| ab-leg-R-01 | hip-abduction.R | = | t: nv；e: 裙甲側片剪切 | 同 | Y | Y |
| ab-leg-R-01 | hip-axial-plus.R | = | nv / nv | 同 | Y | Y |
| ab-leg-R-02 | hip-axial-minus.R | = | nv / nv | 同 | Y | Y |
| ab-leg-R-02 | knee-flexion.R | = | t: nv；e: KC | 同 | Y | Y |
| ab-leg-R-02 | ankle-dorsiflexion.R | = | t: nv；e: 靴面壓縮、腳跟小缺口 | 同 | Y | Y |
| ab-leg-R-02 | ankle-plantarflexion.R | = | nv / nv | 同 | Y | Y |
| ab-leg-R-03 | toe-extension.R | = | 看不出腳趾動作 | 同 | ? | ? |

## 區域判定（依觀察到的側別型態）
**軀幹（兩側無差別）**：typical 四個脊椎動作都可出貨。不可接受：extreme 時胸甲整片像橡膠彎曲、剪切，近看就是軟塑膠鎧甲。最該修：胸甲改剛體跟隨（單骨權重或獨立胸甲骨），變形留給腰部。

**頭頸（兩側無差別）**：typical 全乾淨。不可接受：extreme pitch 下巴沉入護頸、extreme yaw 下顎歪斜。最該修：護頸綁在胸甲、不吃頸部權重，並限制 pitch 範圍。

**左右臂（兩側無差別，左右臂行為一致）**：typical 全部可出貨，前臂旋轉看不到糖果紙扭轉。不可接受：肩屈曲／外展 extreme 肩甲不跟手臂、懸在腋下、腋下拉出細薄片；肘 extreme 前臂甲切進肩甲；combo-arms-overhead 兩側同時雙肩甲懸掛，舉手動畫必露餡。最該修：肩甲給獨立骨骼（鎖骨／上臂混合驅動），腋下帶子重刷權重。

**雙手 [S] 光滑型**：可接受：手腕四向、MCP/PIP/DIP、拇指三關節、拳頭、握劍四向全部可擺，無尖刺無接縫，gameplay 距離全可出貨。不可接受（近拍）：手是充氣氣球——掌部方正鼓脹、指節無定義、拳頭糊成方塊；MCP 屈曲四指折成一片平板；PIP extreme 折成硬角楔形；手腕 extreme 像橡皮管無褶皺。最該修：掌背／指節補形體或法線細節，MCP/PIP 加體積保持。

**雙手 [L] 粗糙型**：可接受：手腕 radial/ulnar、DIP.R、拇指 MCP 在 typical 可出貨，手指分離感比 [S] 好。不可接受：thumb-cmc-opposition.L 在 typical 就有虎口尖刺；wrist-extension extreme 左右手手背夾陷；fingers-spread.R extreme 外側手指剪切成碎片；左手所有近拍都看得到手腕硬接縫與臂甲裂縫；缺 DIP.L、兩側拇指 IP、無法握拳／握劍——劍士角色功能性不合格。最該修：補齊指骨鏈與握劍姿勢，再修虎口尖刺權重。

**雙腿（兩側無差別）**：typical 全部可出貨。不可接受：hip-flexion extreme 裙甲裂出暗色楔形缺口；knee-flexion extreme 小腿塌進大腿、靴子切裙襬；hip-abduction extreme 裙甲側片剪切拉伸；toe-extension 完全看不出動作。最該修：裙甲分片骨骼（或布料）跟隨大腿，膝蓋加體積保持。

**組合動作**：[S] 全部可擺；[L] 四個握劍組合與左右拳頭全部 NP。combo-two-hand-chop 手太小無法判斷變形；唯一可見差異是劍握點方向（[L] 刃朝側向、[S] 刃朝上），不是變形缺陷但影響動畫可用性。最該修：以 [S] 為基礎，補 combo 大圖近拍再審。

## Uncertainty
- 手部近拍的 A/B 相機並不相同（背景、角度不同），手部比較是「同動作、不同視角」，判斷有折扣。
- [S]/[L] 標記是用劍方向、袖口、手指粗細推論；combo-empty-fist.R 的 B 側劍方向反而像 [L] 的相機，歸屬存疑。
- [L] 能擺 fingers-dip-flexion.R 卻不能擺 fingers-dip-flexion.L，疑似左右骨骼不對稱或命名問題，需查 rig 確認。

## Risk
解析度約 320px/格，細微的糖果紙扭轉、小面積穿插可能漏判；toe-extension 與 combo 全身圖太小，無法判定。

## Next step
請 coordinator 對 thumb-cmc-opposition.L、wrist-extension extreme、fingers-spread.R extreme 補 2 倍解析度單格圖，並以同一世界相機重出手部 A/B，再決定是否以 [S] 為交付基礎。
