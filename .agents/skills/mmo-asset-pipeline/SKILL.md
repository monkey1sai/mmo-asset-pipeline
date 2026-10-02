---
name: mmo-asset-pipeline
description: 舊版 Unity 專用工作流；僅在委託明確指定舊 brief、tools/pipeline.py 或 docs/workflow.md 時使用，保留 Unity MMORPG 角色、換裝、場景及交付契約。一般美術需求使用 art-engineer。
---

# MMO Asset Pipeline

此入口保留舊版 Unity 專用契約。一般人物、道具、建築與場景委託使用 [art-engineer](../art-engineer/SKILL.md)，以 [需求驅動工作流](../../../docs/art-workflow.md) 決定必要步驟；沒有指定 Unity 時，不套用下列 Unity／FBX 門檻。

以 [workflow](../../../docs/workflow.md) 與資產 brief 決定目前階段。先執行 `python tools/pipeline.py check-brief <brief>`；需要製作計畫時使用 `plan`。查明目前 Blender/MCP 能力與工具 schema，缺少連線時回報可用的離線工具。

- 概念探索允許多種剪影，production 前補三視圖、拆件線和裝備干涉標註。
- 微調保留原檔；先確認主輪廓再處理細節。生成候選不是動畫就緒的交付物。
- 角色與服裝讀 [角色契約](../../../docs/character-and-wardrobe.md)，區分 skin、rigid、secondary；服裝不得只憑相同骨頭名稱宣稱換裝相容。
- 建築與景觀讀 [材質／場景](../../../docs/materials-and-environments.md)，保留點綴資產、UV／頂點色與材質 variant。
- 小改動讀 [iteration](../../../docs/iteration.md)，只重建受影響階段；PREVIEW 不提升為 production PASS。
- 生成前讀 [Hyper3D](../../../docs/hyper3d.md)。現有授權必須包括具體資料與 credits；此 skill 不授權付費或上傳。
- 交付前讀 [acceptance](../../../docs/acceptance.md)，執行實際檢查並列出未驗證部分。

核心技能在 `vendor/blender-skills/skills/`。按目前階段讀 `blender-director`、`character-artist` 或 `environment-artist`，再按需讀 `retopology`、`rigging`、`animation`、`asset-optimization`、`export-pipeline`、`unity-export`。這 9 個技能已固定來源；其他技能只在需要時另行審查納入。UV、材質、LOD 與碰撞的工作仍須完成，可由目前 Blender 能力執行；不可因未打包獨立 skill 而略過。

專案規格優先於 vendor 的通用建議：Unity production 主格式為 FBX＋明確貼圖映射，GLB 作交換／預覽；T-pose 由 Avatar 實測確認。不同體型可用骨架家族和版本化 bind pose；材料 slots 不等同 draw calls；開口服裝不一律要求封閉 manifold。
