# 角色獨立續作階段

**已結束試作：候選 1/1 完整回歸 FAIL，discard；runtime 接線已恢復原 baseline，baseline 仍 FAIL。** 本輪結論見 [RESULT.md](RESULT.md)，無背景 trial。

使用者於本對話回覆「1」，授權另立最多 2 小時、最多 1 個角色候選；保留舊時計、耗用、失敗與原門檻。本階段不授權付費生成、其他 repo 寫入、commit、push、PR、merge 或部署。

- 開始：2026-10-07T09:54:47Z；硬截止：2026-10-07T11:54:47Z（臺灣 19:54:47）。準備、工具等待、驗證、review 都計入。
- 隔離來源：c5ed6c8f2062692a0941a9fae3d6e06847e5c279；branch codex/role-continuation-20261007。
- 目標：定位 P4 Combo 296 / Idle 3、50:50、雙足鎖定姿勢的 core ID5297 閉環差異；只在因果成立後形成一個原因修正候選。
- baseline：20261007t054356z P4；118 references 中 2 筆 >10 µm，max 18.731347653251667 µm；歷史結果保留，尚待本輪重現。
- 完成條件：輸入 SHA 相符；base→morph→skin 分層診斷；單一候選沿既有引擎 getVertexPosition 路徑回歸全 118 references 及其餘 P4 verdict；foundation、reference、fixture、10 µm 門檻不變；獨立審查。
- 限制：局部診斷或 CPU/WebGL harness 不代表遊戲接入、美術接受、P5 holdout 或角色交付。D2/G1/H1 歷史接受失敗維持原狀。此候選優先關閉 P4 阻礙，gait 不另外新增第二候選。
- 截止或因果不足：保存真實結果與 NOT_RUN，不降低門檻或重開預算。

pre-plan reviewer 已接受調查範圍，要求保留 reference JSON/bin SHA、不得更改診斷公式消除誤差，並完整回歸 118 references。
