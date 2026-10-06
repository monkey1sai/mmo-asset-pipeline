# RO 劍士：批量生成與 Blender 預檢實測

本次批量 API 操作已完成；角色、骨架與連續技能動畫的完整委託仍未完成。
目前 `v001`、`v002`、`v003` 均為 **NO-SHIP**。原 phase 三次修訂已用畢，
[最終比較](comparison-final.json)為 `stop_budget`、`quality_target_met: false`。
所有檔案在隔離 worktree，未 stage、commit、push。

[最終完整性核對](verification-final.json)：41個產物雜湊相符、66份公開JSON可讀、
82個Python檔案語法有效；主入口／隔離版一致，舊provider及授權檔雜湊不變。
已授權的core恢復檔只檢查存在與大小，沒有讀取內容；此核對沒有連線或扣點。
這些結果證明保存內容可追溯，不能取代美術、變形或完整動畫驗收。

## 目前可檢查的成果與缺口

本次已依使用者回覆 `1` 使用核心備援 API 任務及其精確 DPAPI 恢復檔。
非扣點認證成功、一次提交、三次 live 狀態查詢、三檔下載；服務回報新增0.5點。
與本 phase 前一筆批量操作合計服務回報1.0點。分项未回傳，不推定實際扣哪個池；
月訂／普通現有點數皆在本次授權內，沒有加購或升級。

| 範圍 | 已驗證 | 未通過或未驗 |
| --- | --- | --- |
| 單件 core | [新臉部固定近照](core-source-comparison/new/detail.png)與[舊版](core-source-comparison/old/detail.png)相比，細節較清楚 | 不能抵銷握持與配裝缺陷；不是頂尖品質保證 |
| 局部拓樸 | 精確移除4個頭部fin，15016tri／0非流形，其餘面位置與UV回讀相同 | 此閉合性不能證明可動畫 |
| v002裝配／rig | 58868tri、48FK骨；493個權重頂點限制為自身指骨 | 真實握持仍失敗；個別軸方向錯誤另有追加更正 |
| v003右手原型 | 59120tri、52骨、腕部局部重拓樸；20指骨方向smoke check通過 | 掌根折疊、握持空隙與UV跨島污染；未擴展左手 |
| 最後接觸量測 | 選定754樣本未測得>1mm深穿透，兩條射線判定無分歧 | 四指墊最近距離6.68／10.20／10.97／16.16mm、拇指6.50mm；全區within2mm=0，完整三角面交叉未驗 |
| 工具回歸 | 本次116 tests／1.968s通過；舊39件清單valid | 工具測試不證明角色美術或動畫通過 |

可檢查[最終右手正面](v003-hand-surface/front.png)、[側面](v003-hand-surface/side.png)、
[背面](v003-hand-surface/back.png)；灰模抽取只是額外診斷，不替代固定品質視角。
保留的[原型](../../../assets/processed/ro-swordsman-combo-r005/v003-hand-surface/ro_surface_specimen.blend)
是失敗標本；較適合看全角色造型的是
[v002中性裝配](../../../assets/processed/ro-swordsman-combo-r005/v002-fit/ro_core_fit.blend)，
同樣有護臂／襯衣穿插、沒有動畫。

[v002最終覆核](v002-final-review.json)、[指軸更正](v002-axis-review-correction.json)、
[v003最終覆核](v003-final-review.json)分開保留方法錯誤與成品失敗。
相鄰指骨污染移除仍成立；v002個別軸當時方向反轉，不能把該次姿态當成來源拓樸
單獨失效的證明。v003修正軸後仍未形成實際握持。

[搜尋計數核對](search-count-reconciliation.json)保留「舊報告100、逐筆log94」的差異；
另6次可從保存程式的baseline／選定握點／最後回讀呼叫位置推算，每手50與右手累計80
屬程式推算，沒有完整逐次事件trace。最後30候選有逐筆紀錄，累計報告130；缺口不釋出預算。

[總時間帳](phase-accounting-final.json)保留原00:06:54UTC起始、6h／18h與三次上限。
先前未分配的兩輪間等待時間透明轉入最後一輪，未改舊紀錄，CLI總計14607.710521秒。
右手原型關卡失敗後不擴展左手、不做UV重烘焙、完整連段或VFX；原phase已關閉。
後續需另立可審查的新製作範圍與預算，不能重新命名為第四輪或調低門檻。

## v001歷史實際結果

| 範圍 | 已觀察結果 | 限制 |
| --- | --- | --- |
| Hyper3D | 一筆提交、三次 live 查詢、三檔下載，服務回報扣點0.5 | 總餘額229前後相同不能推定沒扣點；分項未回傳 |
| 同圖分件 | 單一 GLB 中六件實際存在，可分離 | 只代表本次完整性成功，不保證其他批量輸入 |
| 裝配 | 镜射肩甲／護臂後八網格，55,488三角面 | 尚有配裝與衣料穿插，60,000整件上限保留 |
| 骨架 | 48骨、可編輯FK、最多4個正規化權重 | 沒有IK/FK切換；數值通過不能代替變形通過 |
| 預檢 | 實際抬臂、深蹲、雙手下劈及掌柄近照 | 腕掌／拇指、肩袖與衣料失敗；沒有完整連段 |
| GLB 回讀 | 新程序實際回讀八網格／48骨／55,488tri及三張嵌入2K貼圖 | 靜態rest，0動畫；未做全動畫回讀 |
| 工具檢查 | `unittest`116通過／1.885s；舊清單39件valid；`git diff --check`通過 | 合成工具測試不能證明美術品質 |

可查看：

- [來源分件](source-parts/extraction.json)：實際件數、三角面與UV／材質保存。
- [裝配基準預覽](baseline/three-quarter.png)及[固定基準](baseline/independent-review.json)。
- [修整後中性預覽](v001-rig-seams/bind/three-quarter.png)。
- [抬臂](v001-rig-seams/stress/overhead/three-quarter.png)、[深蹲](v001-rig-seams/stress/deep-crouch/three-quarter.png)、[下劈握持近景](v001-rig-seams/stress/downslash/grip-close.png)。
- [本輪獨立審查](v001-final-review.json)、[品質帳](quality-ledger.json)及[重新計算比較](comparison-v001.json)。
- [回讀報告](v001-glb-roundtrip/roundtrip.json)和[回讀臉部](v001-glb-roundtrip/detail.png)。

角色 master 在 `assets/processed/ro-swordsman-combo-r005/v001-rig-seams/ro_rig_preflight.blend`，
原始 Hyper3D 回傳在 `assets/raw/ro-swordsman-combo/rodin-v004/batch/base_basic_pbr.glb`。
這兩者都是保存供檢查的產物，不是驗收通過的交付包。

## 有界實驗與下一步

r004起始時鐘、品質門檻、每輪21,600秒／總64,800秒及最多三次组裝修訂都保留。
v001包含配裝與必要的rig預檢相依工作，各中間版本、失敗程式及診斷均保存。
v001當時關閉為failed，計入一次修訂；當時剩兩次。後續v002、v003已使用，現在剩零次。
沒有完整連段投入，因預檢尚未通過。
`compare`目前仍選原baseline，`quality_target_met: false`，不能把局部改善當作整案keep。

v001關閉時只為core準備單件來源比較：[白底圖](../../../assets/raw/ro-swordsman-combo/design-v005/core-white.png)
與[具體計畫](core-fallback-prepared.json)。依據是中性臉部細節不足；
手／肩問題仍可能是骨位、權重或拓樸，換來源不保證修好。
另外五種來源重用，沒有提交六筆原計畫。
新core實際三角面須≤16,148，才能和既有裝備43,852合計不超過60,000；
API參數不是面數保證，下載後再測。

operation `ro-core-fallback-20261003-001` 現已完成下載、服務回報0.5點。
`core-fallback-prepared.json` 保留當時prepared歷史，当前授權與實際狀態分別見
[授權紀錄](core-fallback-authority.json)及[公開journal](../../hyper3d/operations/ro-core-fallback-20261003-001.json)。
已授權並新增／更新的repo外檔案：

`C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-core-fallback-20261003-001.dpapi`

## API入口與查詢

主repo與隔離版 `scripts/hyper3d_api.py` 一致。主入口是：
`C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py`。
本次 operation 紀錄在隔離worktree，查詢時指定workspace：

```powershell
python -B C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py --workspace C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop status --operation ro-split-batch-20261003-001
```

已下載任務回傳保存狀態，沒有新的live查詢或扣點。不要以新operation重送同一任务。
核心任務同一命令將operation替換為 `ro-core-fallback-20261003-001`。
這是本機cached狀態查詢；不是重新驗證live連線或所有API功能。

## 環境事件

第一次GLB回讀呼叫 `bpy.ops.wm.read_factory_settings(use_empty=True)`，
觸發Blender對repo外擴充依賴目錄的清理，出現`PermissionError(13)`。
已停用此方法並保存[事件](roundtrip-environment-failure.json)。
沒有事前依賴清單，不能宣稱repo外依賴毫無變更；未自行修復、改ACL或控制使用者Blender。
後續[唯讀路徑觀察](extension-readonly-observation.json)顯示上述目錄內的
`aiohttp`、`yarl`、`multidict` 資料夾及各自的 `__init__.py` 目前不存在。
因沒有事前清單，不能確認它們何時消失或歸因於本次清理；這三項及其他全域依賴均未修復。
新的回讀方法不重設偏好，並以正式`disable_bone_shape=True`避免將內建80tri顯示球
誤算成角色幾何。兩次失敗和其修正都保留，靜態回讀成功不覆蓋美術失敗。

目前沒有本任務API、Blender或其他背景工作繼續執行；使用者原有Blender程序不受控制。
