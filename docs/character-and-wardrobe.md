# 體型、骨架、裝備與動作契約

## 骨架家族而非單一假人

`humanoid-v1` 是起始人形 profile，不限制所有角色比例。human、giant、elf 與非人 creature 可建立各自 body／rig variant。骨架命名與 hierarchy 可以共享，骨長、rest/bind pose 或比例變化仍可能破壞服裝相容性；Unity Humanoid 的動畫重定向也不保證 clothing bind poses 可以互換。

服裝相容鍵至少包含 `rig_family + rig_version + body_variant + bind_pose_hash`。`bind_pose_hash` 需由實體骨架的骨名、parent、rest matrices、單位和軸向計算，不能只 hash profile 名稱。Extra twist／skirt／cape 骨骼可加入 versioned variant；必須記錄 export、Avatar、動畫與次級動態影響。非人角色採 Generic rig 或專用動畫，不強套 Humanoid。

`configs/rig_profiles.json` 提供必要 hierarchy 和 socket parent 起點。T-pose 在 Unity Avatar Configuration 實際確認；設定檔中的 `bind_pose: T` 不是證明。

## 部件按變形方式分流

| 類型 | 例子 | 綁定方式 | 必驗證 |
|---|---|---|---|
| skin | 緊身衣、皮革、貼身軟甲 | 人體權重轉移作起點，normalize／限制 influences，再手工修正 | 肩、肘、膝、髖在極限姿勢的變形 |
| rigid | 板甲片、懸空肩甲、頭盔 | 單骨 parent 或單一 influence，依設計選 clavicle／upperarm／head | 金屬不彎曲，抬臂時與頸／胸有留空 |
| secondary | 長袍、披風、飄帶 | 次級骨骼、Unity 支援的 cloth solution，或已烘焙動作 | 大動作、collision、reset、角色傳送與LOD／遠距降級 |

長袍不可直接沿用兩條腿的權重。`secondary` 必須明定 motion_solution；動態不是一律昂貴即時物理，依美術效果和同屏負荷選骨骼、cloth 或 baked animation。Chaos Cloth 屬 Unreal 路線，本專案為 Unity，不把它當可用後端。

自動權重不是最终驗收。軟衣可由基準體轉移，硬甲和裙襬需要不同操作；任何工具遇到未知部件類型應停下並保留現狀。

## 遮蔽身體與換裝

每件裝備聲明 `slot`、compatible body/rig versions、`hide_body_regions`、互斥組與允許搭配。穿長靴可以停用對應小腿 render segment／mask，保留原始身體來源；不要永久刪除基準體。露膚、透明布料、混搭靴高和 LOD 切換需要另外檢查，遮蔽不會解決所有衣服互穿。

Unity 最小實作為同一 Animator／骨架的分件 `SkinnedMeshRenderer`；以明確 bone mapping 和正確 bind poses 接入，共用 rootBone。武器作剛體掛在 socket Transform。不要只按名字替換 `bones[]` 就宣稱相容；需檢查 scale、rest matrices 和 bounds，以及換裝後的動作。

## 動作與換裝矩陣

每個 body variant × 每套服裝 × idle／walk／run／attack／cast／jump，加上抬手、深蹲、轉身、膝彎、最大揮劍與收納武器。固定鏡位錄影，近／中／遠 LOD、正側背視角、不同體型都記錄。容錯分區：臉、手、近景硬甲接縫不接受可見穿模；遠距微小遮蔽可由 art lead 定義閾值和鏡頭條件，不能用统一的零穿模口號掩蓋未測項。
