# RO 劍士真實壓力測試：目前未交付

## 已觀察的證據

- 使用者來源的 19 個原始參考檔以相同位元組複製保存；來源資料夾唯讀。需求指定角色＋骨架＋連續技能動畫。
- 本機 Blender 4.5.5 產出 v001、v002、v003 的真實 `.blend`、GLB、五視角及十二姿勢預覽；不是假模型檔。
- v001/v002：24,206 triangles；v003：22,174 triangles。均有 25 joints 與 25 個有動畫通道的 joints，GLB 採樣 0～4.983333 秒，60 fps 設定、300 frames。
- 乾淨場景匯入、實際 weighted vertices／skin／channels、有限數值與動作變化檢查通過，結果綁定各 GLB SHA-256。匯入器的 `Icosphere` 是實際被骨頭 `custom_shape` 引用的顯示輔助物件，逐一列明後排除；不排除任何角色 GLB primitive。
- 隔離工作區本次86個工具測試通過（新增2項骨架／動畫能力清單回歸），39件既有清單結構有效，skill格式與`git diff --check`通過。這些不證明角色美術品質。

## 不能當通過的項目

v001 頭部／衣襬朝向反轉；v002 修正骨架 rest orientation 後臉部仍有突出的眼球／遮臉髮束；v003 改為杏仁眼與露出五官的髮束。實際預覽仍有程序人偶感、肩甲結構偏差、分段肢體與手劍握持差距。v003 的外觀變化是診斷修訂，不宣稱所有品質維度均改善、已滿足照片標竿或已交付。

最後v004已有實際GLB／BLEND：33,096 triangles、25 joints、300frames／60fps；GLB數值重匯入通過。逐幀渲染300幀並量測bounds／weighted腳底，保存640×640／5秒／60fps／300frames的`continuous-neutral-failed.mp4`，master hash保持不變。完整渲染不代表逐幀美術審查；固定五視角、12姿勢及轉場抽查已觀察嚴重扇形拉扯、肩肘跨部位三角片、腰間原手／鞘殘留和衣襬破碎，獨立審查確認不接受。

六維人工觀察分數依序2／2／1／2／1／0，目標均4。美術、變形與動畫需求fail；未完成技能效果，尺寸包絡、完整匯出視覺及交付包維持not_run。沒有game_ready或delivered聲明。

早期v001～v003未及時登記完整baseline、逐輪compare及含人工檢查的總耗時，不能事後補分數／時間來宣稱有效品質實驗。`quality-ledger-blocked.json`保留空trials與真實診斷production_attempts，實際3／3修訂已用完。CLI comparison的declared次數0／時間0只代表空trials，不是實際未花費。機器判定`stop_blocked`／`not_ready`；無有效best，並非證實產物遭替換。

## 壓力測試找到的工具入口問題

API 認證有效且總餘額229；照片入口連續在來源與repo副本回 `PATH_OUTSIDE_AUTHORIZED_ROOTS`。唯讀診斷發現global API adapter的 input/output roots、operation與提交上限仍綁定趙雲舊任務。使用者明確指出：API屬於美術工程師工作流權限，不限趙雲；這是本次壓力測試缺陷。

已準備精確dry-run：舊external reservation1.5＋旧journal reservation0.5保留，本次新增0.5，cap2.0→2.5；提交1→2，限定新operation、單圖、單輸出。舊任務已服務即時回七項Done。獨立唯讀審查未發現本次算式／範圍錯誤，但shared adapter並無共同交易鎖，維持單一操作者並重驗hash。

三次自動審查拒絕分別是：過寬全域設定讀取、唯讀路徑診斷包含未授權的控制欄位、最後的授權檔寫入缺少具體明確批准。前兩項經範圍縮小／使用者澄清完成必要唯讀診斷。使用者選擇「方向1」後，已明確批准單檔寫入；精確差異及舊終態重驗後成功 apply、備份與讀回，journal保持相同。健康診斷19 ok／8 notes／6 warn／0 fail，既有選用MCP及thread警告保留。

本次operation `ro-swordsman-reference-20261002-001` 已完成並下載，task UUID `7120b25b-c2af-4393-b0b0-0bbc809fc11a`，七項Done、consumed=0.5，餘額229→228.5。原始GLB13,558,900bytes及附屬預覽的檔案hash綁定下載manifest。沒有重送或新增付費，API候選仍是靜態起點，不能代替指定骨架、連段與美術接受。

## 保存及續作

所有製作、來源、修復候選與證據保存；禁止以工具測試、GLB檔存在或本次審查代替藝術及動畫門檻。未符合「完成測試且無誤後commit push main」，目前不commit、不push、不宣稱遠端已保存。

續作需要新的具體修復範圍與有界預算，保留本輪三次修訂及失敗，不降低品質目標。建議以原始API表面作修訂來源：語義拆件、清除原姿態殘留、重建中性人體與關節面流；先三個壓力姿勢，再連段與效果。需新版本需求／完整baseline及計時，不能重置舊ledger來繼續。

根工作區同期出現另一批API creation workflow變更，已唯讀辨識並保留；本次未覆寫或合併到main。結果保存於隔離`codex/art-quality-loop`工作區。main HEAD仍`c990639962b7ce85eb6beb631057aa4d76a3e86d`；沒有stage／commit／push。所有本任務CLI渲染已結束，獨立審查已停止；原本開著的非headless Blender不屬於本次背景檢查，未操作或停止。
