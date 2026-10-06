# RO 劍士分件製作 brief

目前狀態：設計與公開 API 計畫已準備；尚未提交，尚無新 3D 產物。

## 需求與製作界線

使用者同意由工程師負責設計，交 Hyper3D 生成，再用 Blender 微調。完整交付仍為角色、可編輯骨架、照片中挑釁→狂擊→怒爆→霸體→勝利的連續300幀/60fps/5秒動作及分離可關閉的效果。獨立 BLEND/GLB，未指定遊戲；commit、push 等使用者驗證。

採用 art-engineer、imagegen、blender-director、character-artist；實際綁骨和動畫時沿用 rigging、animation、export-pipeline、qa-review 的相關方法。以本機 Blender4.5.5 控制可編輯資產，不把不存在的 MCP 連線當成已可用工具。

## 設計主假設

將硬甲與柔性人體/衣料從生成時就分開，可避免舊網格中甲片與身體融合後被線性蒙皮拉成軟折面。手部保留清楚開掌輸入；真正手指構造、骨骼中心和握持仍需檢查。六件輸入是不同必要部件，不是盲目重送同一失敗任務。

角色核心含頭髮、臉、內衣、褲、手套和靴；胸甲、單側肩甲、單側護臂、腰帶/衣襬/前襟、長劍另生成。左右裝甲先從同一側來源鏡像衍生，再核對手性、法線、材質、接合及全範圍動作。完成甲片內側和接合修整，維持剛性跟隨；衣料以專用控制安排讓位。若生成拓樸不支持必要關節，不宣稱只是微調就能解決：保存缺陷，評估局部重建或更清楚的輸入。

## 固定規格

角色身高1.74m，角色與劍總三角面不超過60,000；展示場景和VFX另記。目標2K貼圖、+Y上/+Z前GLB、地面中心角色pivot、劍柄掛點。六維最終品質目標均為4，不降門檻、不事後改舊分數。

五個固定視角、光照及相機延續r003；功能預檢新增開掌、握拳、單/雙手握劍、過頭、下劈、深蹲、落地。先保存源件與组裝 baseline，再做三個有明確主假設的組裝修訂。新版 phase 是使用者同意的新製作方法；r001/r002/r003 的候選、成本、時鐘與失敗全部保留。

## 階段與完整交付

requests/ro-swordsman-combo-r004-preflight.json 僅驗組裝/骨架/變形及短姿勢輸出；不能代替 requests/ro-swordsman-combo-r004.json 的完整連段與效果。階段改善逐項比較且無退步；最終必須全部必要驗收完成。程序讀到有效 schema、權重正規化、骨骼數或渲染成功，都不等於美術/功能PASS。

## 後製與驗收順序

1. 逐個來源GLB核對實際面數、尺寸、材質、表面開口及相連部位；建立實際5視角源件基準。
2. 組裝衣甲與劍；先在中性姿勢核對比例、側背輪廓、內側接合與貼圖。
3. 校正關節中心/骨軸/權重；獨立甲片使用剛性跟隨，柔性布料使用可匯出的衣片骨。實際握持使用主手武器控制與副手握點，檢查掌指/柄表面及肘的彎曲方向。
4. 完成所有功能預檢，通過才製作無效果完整連段。支撐腳、骨盆重心、劍尖軌跡及過渡逐項檢查。
5. 匯出GLB、乾淨重匯入整段回讀；效果可關閉，另驗效果版。保留master、原始圖/模型、相依檔及使用說明。

## 目前 API 與授權

六筆計畫已存 runs/hyper3d/plans，各估算0.5點，初次總計估算3點；不是新增點數限制。實際成本以服務 consumed 回報，逐筆記錄。只使用已授權的現有月訂/普通點數，沒有加購或升級。2026-10-03 非扣點認證回報229，餘額不是任務成本。

尚缺這六個新任務恢復檔的逐檔外部寫入授權；沿用使用者先前要求，不重問點數。未知/pending 不重送；檔案碰撞、不同來源或服務身分不符時停止該操作並保留紀錄。舊授權檔/憑證/任務檔不改。

## 設計圖提示

Built-in image_gen。每張以舊A-pose設計作身份/風格參考，單件、透明背景、完整邊界、清楚形體與中性光照。保存實際PNG與hash；透明alpha和外緣柔光已列為輸入檢查項，不能用生成圖推定3D拓樸。

### core

Full-body ONLY the unarmored inner character of this swordsman. Remove ALL silver metal armor, shoulder plates, bracers, all long coat tails, waist tabard, belt/scabbard/sword. Navy close-fitting long-sleeved tunic to hips, brown straight trousers, knee-high brown leather boots, brown leather wrist-length full-finger gloves. Preserve face and spiky hair. Adult youthful proportions, about6.5heads tall. Natural symmetric A-pose arms45degrees downward and clear torso gaps, elbows slightly bent, feet shoulder width apart flat. Both gloves open with five anatomically correct separated fingers in each, fingers relaxed, palms facing front; thumbs clearly separate at natural opposition angle. No dangling garment across hips or knees. Front orthographic camera.

### cuirass

ONLY one empty wearable sleeveless silver breastplate cuirass. No human, no mannequin, no arms or shoulder plates. Rounded shaped breastplate with subtle central ridge and one lower overlapping abdominal plate, clean bordered edge like reference. Hollow neck opening, arm openings and open lower waist clearly readable, interior visible at neck/arm hole. No straps extending into empty space, no fantasy spikes. Slight front three-quarter view showing its depth; centered upright torso shape.

### pauldron

ONLY one silver shoulder pauldron armor assembly for the character's RIGHT shoulder. Rounded upper cap and two overlapping articulated lower lames, restrained edge trim and two tiny rivets, matching the reference. Wearable hollow underside visible, no arm or torso, no cloth, no strap floating in space, no stand. Slight front three-quarter isolated product view.

### bracer

ONLY one silver wearable RIGHT forearm bracer. Short tapered rigid shell from wrist toward below elbow, one clear curved center ridge and bordered edges, two restrained brown leather fastening bands wrapping its exterior. Hollow cylinder with wrist and elbow openings, no hand, arm, mannequin or shoulder plate. Diagonal three-quarter product view with both length and hollow opening readable.

### coat

ONLY one empty wearable waist garment assembly for this swordsman: brown leather waist belt with restrained brass rectangular buckle, two separate navy blue cloth tails with ivory narrow edge trim hanging at left and right thighs, a narrow ivory front tabard with navy edging between them. Fabric panels rest apart with visible full-height air gaps, open front sides and no closed skirt bell. Length from waist to just above knee, believable soft fabric folds, no trousers, legs, boots, torso, hands or stand. Front orthographic product view, entire belt and all three cloth panels visible.

### sword

ONLY one complete straight medieval anime longsword matching the reference: slender double-edged brushed silver blade with crisp central fuller, restrained brass straight crossguard with flattened gently flared ends, long brown leather-wrapped grip fitting two hands, small brass faceted pommel. No character, no hand, no sheath, no light/effect. Full sword vertical blade-up, near orthographic product view at slight angle so blade thickness is visible. Proportions blade about80cm, grip22cm, crossguard19cm, clear physical details.


