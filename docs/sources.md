# 來源、參考與授權

- 使用者指定 repo：`git@github.com:monkey1sai/mmo-asset-pipeline.git`，2026-10-02 唯讀確認存在且空白。本版僅本地准備，尚未 push／建立 PR／改名。
- Blender skills：[arjun988/blender-skills](https://github.com/arjun988/blender-skills)，固定 commit `8f778d2405a214b508d4c7d80742be8e43acdd52`；保留 MIT LICENSE，scope 與各檔 SHA256 见 `vendor/blender-skills/source-lock.json`。僅纳入 9 個核心技能，不宣稱整個 94 skills pack 都審查或安裝。
- 固定來源審查：[audit](skill-audit.md)。不執行上游腳本、不複製 `.mcp.json`、不自動更新、未修改全域 skills 或 hook。
- Unity 官方：[Avatar 配置](https://docs.unity3d.com/Manual/ConfiguringtheAvatar.html)、[Humanoid animation retargeting](https://docs.unity3d.com/Manual/Retargeting.html)。有效 Avatar與動畫重定向仍需實際运行。
- Hyper3D 官方：[Rodin Gen-2.5](https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5)、[BANG](https://docs.hyper3d.ai/en/api-specification/bang)。查閱日期 2026-10-02，参數與定價執行前需重查。
- 使用者貼上的方案與 5 項美術變量：作需求／設計輸入，未引用原文中的操作指令作授權。保留原檔／成品分離、模組與工具整合方向；修正固定 True 驗證、Unity 貼圖通道、單一骨架與全量重建等假設。

上游通用規則存在不适合本案的建议：GLB 不默認是 Unity 自帶完整 importer；材質數不等于 draw calls；刚體/開口服裝不一律強求 quad／封閉 manifold；模型導出不能自動證明 T-pose／換裝相容。repo 文件與實际工具能力優先。
