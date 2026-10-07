# 交接給 Codex：RO 劍士角色動畫 V1——連段完成後的待辦

> 本文是交接文件，不是授權。commit／push／PR／Hyper3D 付費與任何門檻放寬都要使用者當次明確授權。

## 給 Codex 的 prompt（可直接貼）

```
你是 C:\Repos\mmo-asset-pipeline 的美術工程協調者，接手 worktree C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop（分支 codex/art-quality-loop，origin 同步於 75b8950；PR #7 已合併到 main 08c454e）。
先讀 AGENTS.md、docs/handoffs/codex-character-animation-v1-combo-20261007.md（本文）、requests/ro-swordsman-character-v1-r6.json 與
runs/qa/ro-swordsman-character-v1/authorizations.json（第 24–29 筆），再讀 runs/qa/ro-swordsman-character-v1/v001/p4/milestone-04-progress.json、
runs/qa/ro-swordsman-character-v1/v001/clips/AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory/combo-progress.json 與 v001-pause-29.json。
規則：單一 writer；r010 不重開；門檻與豁免不放寬（D2／G1／H1 的已知失敗維持列出，不修飾）；Hyper3D 只用使用者已授權的點數且付費提交前先存 operation ID；
commit／push／PR 等使用者當次授權；Blender 用 "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --factory-startup --disable-autoexec，禁用 read_factory_settings／read_homefile／save_userpref；
回覆用繁體中文（台灣）並按 AGENTS.md 的五段摘要；時鐘延續 v001-pause-29.json（上限 129,600 秒，已用 53,487 秒）。
待辦依序：
1. 在可見的瀏覽器窗格跑 run-07 的 runtime 閉環（見下方指令），存檔後把結果路徑補進 milestone-04-progress.json 的 runtime 區（目前標 run_07_pending）。
2. 把連段 a07 的審查圖（clips/.../combo-review-sheet.png）與 p4/milestone-04-sheet.png 交使用者美術審查；接受後請使用者授權 commit／push，再分組提交未提交的 38 個路徑。
3. 使用者決定 P5（凍結與 holdout）後才開始 P5；凍結前先核對 holdout_policy 與 foundation signature 工具（scripts/cv1_foundation_signature.py）。
不要做：修改凍結的 two_hand_chop 姿勢或 b20 foundation（D1 未授權）、重跑已被取代的中間輪次、刪除證據。
```

## 現況（2026-10-07T05:29Z）

| 項目 | 狀態 |
|---|---|
| 第三、四里程碑 | 美術審查接受（第 23、27 筆），已推送並合併 PR #7（main 08c454e） |
| 連段 `AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory` | a07 依第 29 筆（H1）結案：手部、腳步、劍對身體通過；collapse 254/671 取樣（184 為凍結架勢自帶三角形 28476，面積比 0.047）、握持 3 個過渡取樣，列為已知失敗。匯出 a07/export、回讀 3.69 µm、runtime 閉環 6.03 µm 通過 |
| 效果層 | `a07/fx/ro_skill_effects.glb`（25 物件、344 面、獨立 GLB，事件計時） |
| 轉場 run-07（191 組，含 Idle↔Combo） | 126 通過；已知失敗：皺褶區 collapse、1.5 倍速腿長極限、連段架勢自帶 collapse、400 ms 淡入跨過連段開頭跨步（腳 130–222 mm）、400 ms×1.5 淡出跨過左手離柄（握持 42 mm） |
| run-07 runtime 閉環 | **未跑完**：瀏覽器窗格隱藏時頁面量測停滯。需在可見窗格重跑 |
| 美術審查（連段、連段轉場） | 待使用者 |
| commit／push | 未授權；38 個路徑未提交（`git status`） |
| Hyper3D | 未使用；餘額 224（2026-10-07T02:36Z 唯讀） |

## 可重跑的指令

- 單元測試：`python -B -m unittest discover -s tests -v`；清單：`python -B scripts/pipeline.py validate`
- run-07 runtime 閉環：`preview_start cv1-runtime-qa-p4`（.claude/launch.json，port 8772）→ 開 `http://localhost:8772/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json` → 按「執行 P4 量測並存檔」→ 結果存到 `p4/runtime/<stamp>-p4-results.json`
- 連段重做：`prep/spec-a07-used.py` 產生 clip.json／interaction.json（互動設定改動須 `cv1_interaction.register(..., reason=...)`）；作者 `scripts/cv1_author_clip.py`；檢查 `scripts/cv1_clip_check.py`；探針 `prep/reach-probe-used.py`、`prep/arm-pose-probe-used.py`、`prep/clip-frame-probe-used.py`
- 轉場：`scripts/cv1_p4_scenarios.py` → `scripts/cv1_transition_check.py --shard i/n --reference` → `scripts/cv1_p4_manifest.py` → `p4/feet-recheck-used.py`、`p4/classify-collapse-used.py`、`p4/progress-07-used.py`

## 已知限制與未決

- 凍結的 r010 握法使劍身大致與前臂反向：斬擊終點只能做成向右前下方掃出；怒爆的劍壓到接近水平。
- 凍結的 `two_hand_chop` 在 b20 上自帶一個 0.047 的三角形折疊與（無修形時）4 對手部自交；修形開啟後自交為 0。
- Idle→Combo 長淡化的腳步失敗可用「淡化不跨過目標片段第一次 stance 變化」（C1 擴充）或連段開頭保留 40 幀 Idle 停頓解決；兩者都需使用者決定。
- 工具修正：`cv1_author_clip.py` 部分權重姿勢改為從目前旋轉混合（影響新片段，既有片段只用單一姿勢不受影響，未重跑）。
