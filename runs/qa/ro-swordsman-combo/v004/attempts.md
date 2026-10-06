# 最後候選 v004：同一候選的建構診斷

主假設：保留照片生成的角色表面，修復融合的活動分區，再以匹配 bind pose 的骨架完成照片技能；必要相依修正包括UV保留、內側表面、白前襟、法線強度及獨立直劍。

候選次數沿用 v001 baseline＋v002＋v003＋本次v004，沒有新開預算。任何建構重試仍計入v004總時間；目前不是已評估完成的candidate，也不宣稱所需美術目標達成。

1. `PRODUCT_FAILURE`（實際新建候選幾何）：第一版 `holes_fill` 在具有分叉切口的區域產生49～238條非manifold邊；逐件結果保存於 `topology-pre-rig-attempt01.json`、`construction-attempt01.json`、`console-attempt01.txt`。未匯出交付。
2. 新方法：沿原面拓樸逐boundary halfedge追蹤同一face fan，重複頂點拆成個別圈，每圈新增獨立中心與三角補面，避免共用已有對角線。仍需重新核對非manifold及實際變形；閉合不是無穿插的證據。
