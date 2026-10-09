# S2 過渡面與肩背掛點定位 checkpoint

接續 [S2 接縫 checkpoint](zhaoyun-s2-seam-checkpoint-20261010.md) 與 [執行步驟](mixamo-secondary-execution-steps-20261009.md)。本輪起點為 main `c255925328804ce880a92a89adf7654640d57545`，PR19／20 均已合併，同 SHA main CI run `37962354261` SUCCESS。本輪為使用者指定的 S2 唯讀診斷，不新增角色候選。S2 **PARTIAL**；D0–D5 仍 **1/6、NOT_COMPLETED**。

## 本輪實際進展

以已核對原始 ID 的 Blender baseline、原材質與 UV，產生並實際檢視 26 張新圖：v003／v004 各九張目標面及掛點圖，加上八張肩背局部／上半身四向圖。Blender 5.2.2 LTS 使用獨立 `--background --factory-startup --disable-autoexec --python-exit-code 2` session。三次退出碼均為 0，耗時分別 22.040、23.118、16.731 秒，均在各自 1200 秒唯讀診斷上限內；不重設已用完的修復 trial 或舊 60 分鐘窗口。

1. 原始 face `22680`（頂點 `2364,2783,2361`）的單面法線／反向圖解除遮蔽，確認可見白綠貼圖過渡。它的物理接縫身分仍未確認，因此新增為 **HOLD_NO_WEIGHT_OR_TOPOLOGY_EDIT**。先前四個綠色面 `22105,22106,22673,22679` 仍保守排除於白色內層修復範圍；這是範圍限制，不能據顏色認定它們必然是不同衣物。
2. 真實 target rig 沒有通用 profile 的 `clavicle_l/r`。v003 實際只找到六個端點，v004 改以既有 `upperarm_l/r`、`spine_03`、`neck` 作肩背幾何參考，共十二個實際端點，明列缺骨。沒有新增、改名、重新映射骨頭，沿用既有本地角色 motion profile。通用 profile 不是此角色骨架真相。
3. `cape_01` 根部約在 world `(0,0.1000,1.3014)m`；已保存每個端點最近八個面板頂點、距離、原始配重與 incident faces。最近點只是定位，不能直接指定固定配重；末端距離只對局部面板量測，不能推論骨長錯誤。
4. 根部半徑 0.22m、任一面頂點落入球內的診斷集合有 1391 面；上半身任一頂點 z≥1.05m 有 9989 面。四向原材質圖顯示球域混有披風、胸甲、衣領，不能當披風遮罩。裁切造成的邊界不是原模型裂縫。肩甲下的真正固定接合面仍有遮蔽，尚未接受。

目標面近照以該三角形尺度構圖，部分鄰面超出畫框。掛點 front 標籤接近右邊框、back 根部標記部分遮蔽；位置以 report 座標為準。沒有將這些畫面限制改寫成 PASS。完整角色各部位與固定區語義審查仍未結案。

## 本地證據與交付

路徑相對於既有美術隔離 worktree；原素材、PNG 與完整幾何資料公開再散布權尚未確立，這個公開 PR 僅提交本 checkpoint 文字，不包含素材或影像。

| 檔案 | SHA-256 |
|---|---|
| 原始 GLB | `7dccbfae4b61280889a7be98370692143898c3eeef8dcd55dfa36ad4b4248a33` |
| `runs/qa/zhaoyun-s2-anchor-face-review-v003/report.json` | `c7df7890403eda13df35e49c981c2ab4b88ca58524f9b588a01dccef96a4dd46` |
| `runs/qa/zhaoyun-s2-anchor-face-review-v004/report.json` | `15d33db1bf5afe9c9a74107ca63ab9bd1df39b61923956f5521f793ae4fa1921` |
| 同目錄 `semantic-review.json` | `5daa158f44c44398c46487b342abc8d6a002f74921be3ddba121860441abb0d5` |
| `runs/qa/zhaoyun-s2-root-context-v001/report.json` | `76a30b4a52e13a5b490792072cd0cd03494dbd19ddd76880d03a359dc62ade14` |
| `runs/qa/zhaoyun-s2-anchor-tests-v001.log` | `8b5cd8ec8128f04d570edc510f4f7851c4f617f39e9aef8467e5af17ba823c1b` |
| `runs/qa/zhaoyun-s2-anchor-validate-v001.json` | `106bb3a13bb5b30e058ed51556ccd0917934d8b64cd8129ff29e3aab46503568` |
| `deliveries/cl-zhaoyun-secondary-v001/v007/manifest.json` | `190f385d824261ce18a846499711aaadcb944ea8153070942c0edfdd7976ccee` |

v007 以新 delivery ID `cl-zhaoyun-secondary-local-v007` 保留 v006 每一檔案原始 bytes，加入三次診斷、26 張圖、報告、審查、操作與封存腳本、log：**86 檔、43,081,089 bytes，逐檔 SHA 回讀 PASS**。歷史版本沒有覆寫。`package_complete=false`，依賴既有 repo、來源 baseline 及相依工具；不是獨立可執行 Unity 成品。案例腳本位於本地 `runs/evidence/zhaoyun-s2-anchor-face-review-v003.py`、`v004.py`（完整檔名同前綴）、`zhaoyun-s2-root-context-v001.py`，不是第二套核心 pipeline。

## 驗證狀態與承接

- 工程：在上述 main SHA 重新執行 `python -B -m unittest discover -s tests -v`，**379 tests PASS、0 skipped，12.070 秒**；`python -B scripts/pipeline.py validate` PASS，39 assets／11 operations，只驗 schema／catalog／ledger。本 PR 沒有工程程式變更。
- 真實 DCC：三次唯讀渲染執行完成、26 張圖實際檢視，原 GLB 與 baseline blend 前後 SHA 相同；固定區／完整語義遮罩 **NOT_ACCEPTED**，美術修復未完成。
- 角色修復：兩個歷史候選均 FAIL，舊額度剩餘 0。沒有第三候選、權重／拓樸／骨架／UV／材質／武器修改；原 authored master 仍未找回。
- Mixamo 實際上傳、綁骨與走跑跳整合 **NOT_RUN**；Unity 完整遊戲接受 **NOT_RUN**；`game_ready=false`。

下一步仍是 S2：定位肩甲遮蔽下的接合面，補全衣料、剛性甲片、髮束與繫點的語義邊界及保護區，再提出單一且有界的 S3 修復範圍與新額度。只有接受同一候選的 D0–D5 全部必要驗收（包含 Unity 完整遊戲）才可標 SPEC COMPLETE。回滾為不採用診斷集合、繼續使用原資產；不刪歷史證據。
