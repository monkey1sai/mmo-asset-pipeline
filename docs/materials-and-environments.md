# 材質表現與場景自然感

## Shader 與貼圖契約

2K PBR 是起始 profile，不是所有表面的硬上限。skin、silk／anisotropy、emissive rune、translucent veil、jade／crystal 可使用具名 shader profile、額外 masks 和貼圖通道。每個 variant 記錄使用的 Unity 版本、URP／HDRP、shader 名稱／版本、貼圖色彩空間、透明模式、normal／smoothness 意義和性能數據。

attachment 的 `MRAO: R=Metallic, G=Roughness, B=AO` 是交換約定，不可直接當作 Unity 通用材質輸入。Unity shader profile 需明確重新打包：例如 URP Lit 的 metallic／smoothness channel 與 occlusion 使用各自規範；roughness→smoothness 是 `1 - roughness`，但具體 packing 與 HDRP / 自訂 shader 不同。貼圖工具必須接受具名 layout，不默默重解讀所有 MRAO。

UV0、UV1 和 vertex colors 各自聲明用途。UV1 若同時需要 lightmap 與 detail mask，必須重新分配通道。美術可在引擎內畫髒污／青苔，shader 必須保持有效的 vertex color 輸入，不能匯出時丟失。貼花、透明與多層材質在目標硬體量測 overdraw、draw calls、GPU time；材質 slot 數只是構造數據。

第一版未選 URP/HDRP、未實作 shader 或貼圖打包器；先保留契約並在試產時選定 render pipeline，避免把概念上的特殊材質宣稱已可用。

通道對照需按實際版本查閱 [Unity URP Lit 官方規格](https://docs.unity3d.com/6000.0/Documentation/Manual/urp/lit-shader.html)，不要將交換貼圖通道當成所有 shader 的共同約定。

## 建築與景觀

模組格網用於结構相容，不把所有外觀鎖成方塊。牆、角、門窗、屋頂與路段先做最小拼裝 kit，再加入 `accent assets`：招牌、碎石、藤蔓、青苔、歪斜外飾、布幔、獨立英雄資產和貼花。

「80% 模組＋20% 點綴」是起始美術配方，不是硬性計數規則；根據鏡頭、地區故事和同屏成本調整。英雄地標和有機地形允許非格網轮廓，仍須正確 pivot／連接面／碰撞。對接的結構面不能任意偏移而讓接縫或 navigation 壞掉。

環境驗收：用 kit 拼封閉房間、L 型路段與 T 路口；從玩家镜头沿探索路線檢查接缝、穿越、重復圖案和視線。固定几個地區樣板，評估重複識別度，不只看單件 hero render。Trim sheet／共用材質是重用手段；頂點色、decal、局部 UV 變化、形状和道具布局共同提供變化。

景觀大面積地形通常適合 Blender／地形工具的程序策略，Hyper3D 可用於岩石、樹根、英雄道具等獨立候選。整座城鎮或整張遊戲地圖的一次生成，沒有證據保證 grid、collision、導航和串流相容。
