# P4 run-07 來源診斷與下一次最小量測

唯讀診斷者：`/root/bounds_diagnosis`；主控保存非秘密任務摘要。未做新 runtime trial、Blender pose 求值、候選或 synthetic pose 計算。

## VERIFIED：已有結果的觀察

來源：`runs/qa/ro-swordsman-character-v1/v001/p4/runtime/20261007t054356z-p4-results.json` 及同目錄 reference 資料。

- 失敗 block：`transition/combo-idle-end-b100-s1.0@0.55`、`transition/combo-idle-end-b200-s0.5@0.6`。
- 兩者均是 Combo frame 296 與 Idle frame 3 約 50:50、雙足鎖定；最大誤差 18.731347653 µm，最差 `SM_RO_core`／原 vertex 5297，1751 個 export vertices 超過原 10 µm 門檻。
- frame diff ≤2.665e-15、layer weight diff=0、morph weight 最大差 1.606241484e-7、foot target 最大差 0.310349 µm。
- 同 pose 其他 8 個 mesh 最大誤差 ≤0.575075 µm；core RMS 約 7.611086 µm。
- 六個 harness 檔案 SHA 及 Idle GLB SHA 與 run-07 記錄相符；未完整回讀其他 GLB／Python 執行來源 SHA。
- 34 個 core morph 中，reference 僅三項非零：fold_02=0.05213447680082128、fold_04=0.0005071564022202102、fold_06=0.04371666247673178。這是 reference weights；逐項 runtime weights 未在既有結果保存。

## 可定位程式

- `tools/runtime-qa/three/src/p4.js:189`：action frame／layer weight，AnimationMixer update。
- `tools/runtime-qa/three/src/p4.js:179`：混合 interaction state，再求 helpers／correctives。
- `tools/runtime-qa/three/src/p4.js:394`：frame／layer／morph／foot target 與 vertex 比對。
- `tools/runtime-qa/three/src/p4.js:534`：vertex closed-loop 與 frame／weights／foot targets 分開判 gate；morph 門檻 1e-4 的 PASS 不推出 vertex PASS。
- `tools/runtime-qa/three/src/cv1-runtime.js:209`：getVertexPosition、matrixWorld、軸映射及逐原 ID Euclidean error。
- `scripts/cv1_transition.py:127`：quaternion slerp；第 152 行按 layer order 模擬 PropertyMixer。
- `scripts/cv1_transition_check.py:150`：integer-frame sampling 及 blend；第 181 行寫入 Blender pose；第 241 行 correctives；第 665 行 evaluated vertices 保存為 float32。

## INFERRED：假設與排查順序

優先比較 core morph 求值／delta、core skin influences／正規化，再核對局部骨混合／precision。frame 和 layer controller、全域軸映射及純播放歷史 drift 的優先度較低；不能據此完全排除特定 bone matrix 的差異。reference float32 rounding 也未正式排除。

根因仍 **UNKNOWN**。尚無逐 vertex error vector、core 各 runtime corrective 實值、逐 bone matrix 或 foundation weights 對照；本輪未證明修復或重新復現 runtime gate。

## 取得角色准入後的一次有界診斷

鎖定既有 Combo296／Idle3 pose、原 vertex ID 5297，保存同 ID 的 base position → morph 後 → skin 後／world position，並記 corrective 實值／delta、joint weights 與相關 bone matrices。定位差異首次出現的層，才選最小修正。

禁止靠放寬 10 µm gate、任意歸零 fold_04、重新正規化 weights 或修改 foundation 蓋掉失敗。准入尚未完成，動態診斷維持 HELD；沒有背景 trial。
