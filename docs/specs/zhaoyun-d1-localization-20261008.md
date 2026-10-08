# 趙雲 D1 局部定位 checkpoint

日期：2026-10-08。Spec `mixamo-secondary-character-workflow-v1`：**1/6，NOT_COMPLETED**。D0 已結案；本 checkpoint 完成 D1 的原材質幾何定位與局部假設，沒有修復候選、語義遮罩接受或 D1 結案。

## 工具與操作

擴充既有 `scripts/blender_component_review.py`，增加選用 `--focus-profile`。保留原材質，在複製 mesh 的指定原始 ID incident faces 著色，產生前／後／側近景及全身位置圖。原始 mesh、weights、UV、materials、rig 不修改。面索引域仍是 Blender 匯入 polygon index，不能當原 GLB 三角 ID。

Profile 格式：

```json
{
  "baseline_sha256": "<已核對的 indexed baseline blend SHA-256>",
  "mesh": "<mesh name>",
  "regions": [{"id": "local-region", "edge": [0, 1]}]
}
```

兩個 ID 必須是存在的原始頂點且為實際 mesh edge；region ID 不得重複或包含路徑內容。Profile 綁定 baseline hash 與 mesh，避免把其他版本的選區套到目前模型。

操作：在既有 command 加上 `--focus-profile configs/<case-focus-profile>.json`；新輸出位於 `runs/qa/<new-run-id>`，拒絕覆寫。至少產生三張幾何區域圖，另對每個 region 產生三張近景和一張全身圖。被遮擋的視角仍保留，不能因沒有看到標記便宣稱該面不存在。

## 真實案例的定位結果

鎖定模型 SHA-256 `7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33`。本地實跑 Blender 5.2.2 LTS，共 11 張圖、新 review blend 與 report，baseline unchanged=true。已檢視四張原材質近景。

| 區域 | 觀測與可核對的分支線索 | 限制 |
|---|---|---|
| 1352↔1116 | 前視近景在白色衣料表面；還原 prepare 腳本 floor 後 z 約 -0.180843／-0.178506，跨 `z < -0.18` 分支；權重分別以腿／手臂為主 | 白色衣料細分為披風、裙衣或錯接區的完整邊界仍未接受，不能按此整體重配 |
| 14801↔14876 | 小腿甲與衣料交界近景；x 約 -0.167856／-0.171386，跨 `abs(x) < 0.17` 分支；原權重分別 cape_02=1 與腿群 | 部分視角遮擋；不能只靠材質或鄰近點決定移除面或転移權重 |

已唯讀核對 prepare 腳本 SHA-256 `74acce85ba5ec38c7649188319b7397f2b32f3a5f3074ac4b1984f073649bcde`。以上端點跨分支及現有 influence 是可觀測數值；「空間分類分支造成配重斷界」是受支持的局部修復假設，不宣稱已證明唯一根因或排除 holes_fill 的錯接面。

## 驗證與證據

- 本地正面 Blender 實跑 exit0，profile hash、原始 vertex ID、incident／shared imported polygon index、world center、近景尺度均保存於 report。
- 錯 baseline profile 拒絕 `FOCUS_BINDING`；重複端點拒絕 `FOCUS_VERTEX`；含路徑的 region ID 拒絕 `FOCUS_REGION_ID`。三項皆預期 exit2，harness PASS。
- 本地美術隔離樹 `python -B -m unittest discover -s tests -v`：344 tests PASS；`python -B scripts/pipeline.py validate` PASS。一般 CI 不執行 Blender，不代替本地 DCC 證據。
- 本地 run `runs/qa/zhaoyun-focus-v001`，完整原幾何／圖片／blend 未公開。本 PR 僅工具與去幾何摘要，不含角色素材或私人資料。

## 剩餘門檻與完成定義

D1 仍需接受明確部位遮罩、核對原 trial／time 的實際剩餘額，再在單一假設下修改新候選。現有 draft 的 max_revisions=0 與空 blocked ledger 不釋出新預算，未知歷史耗時不倒填；修復授權已存在，不需重複詢問授權。

D2 製作路線、D3 真實 Mixamo 綁骨／走跑跳與重定向、D4 製作端全段與重匯入接受、D5 Unity 完整遊戲與視覺接受尚未完成。只有同一候選通過所有必要檢查、Unity 指定玩法與人類觀感審查，spec 才能 COMPLETED。

此分支依賴 D0 工具 checkpoint（PR #12）。PR #11、#12、此 checkpoint 依序核對／合併 main，不以未合併進度冒充 main 狀態；人類 approval／checks 沿用既有規則。回滾只 revert 本 checkpoint，不刪本地來源與歷史證據、不覆寫遊戲原 GLB。
