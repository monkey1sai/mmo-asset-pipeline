# RO 劍士手部與配裝：新階段製作設計

使用者已授權方向1，將產製與失败成本視為美術工程師工作流的壓力測試。
本階段不重新開啟r005；其三次失敗、時間、模型及1.0點服務回報全部保留。
完整角色、可編輯骨架、300幀／60fps連段、分離可關閉特效、BLEND／GLB及60,000tri上限不變。

## 設計與製作順序

1. 以獨立右手皮手套為來源。張掌、四指與拇指明確分離；厚實掌根、短腕口。
2. Hyper3D生成候選，實查手背、側厚度、指縫及腕口；Quad選項不作面流保證。
3. Blender先修形體／面流及腕口，骨位和合法權重接著驗；握持前不做材質精修。
4. 固定張掌、小屈指、单手握持及四近照；同時量測真正劍柄接觸和穿入。
5. 右手過關後才鏡射／擴展左手，檢查左右材質方向及雙手配裝。
6. 手部與配装預檢全部通過後，製作三壓力姿勢、完整連段、VFX與GLB動畫回讀。

膚／手套與硬護臂保持獨立。保留新core與已有裝備；不因API可用而全部重做。
生成來源若需要大幅重拓樸，成本帳必須列為額外產製，不能稱為「微調完成」。

## 面數分配與固定關卡

實體baseline為58,868tri。預定切除區域的規劃量測為右492、左537tri，未執行切除。
保留256tri腕縫預算後，不減其他部件時每手最多952tri。
API的1000 target並非輸出tri保證。先量測下載實物；不足時優先另存硬肩甲／護臂的
有限減面版本，核對輪廓／UV／裝配，不犧牲已證明必要的指節面流。

完整局部方法固定在`hand-gate-contract.json`，以SHA綁定baseline與後續紀錄。
接觸距離2mm、深穿透樣本1mm只是局部關卡的一部分；還要檢查真正面交叉與可見變形。
無特效灰模只是額外診斷，不能代替完整裝配五視角。

## 工具與權限

圖像工具：built-in image_gen；Blender4.5.5LTS；本repo Hyper3D client＋既有DPAPI provider。
新API operation：`ro-hand-source-20261003-001`，離線估算0.5點；即時成本以服務回傳為準。
既有按需月訂／普通點數授權沿用。新增精確恢復檔仍等待使用者回答；不修改密鑰／全域設定／舊任務。
新實驗階段最多8修訂、每輪6h、總48h是規劃邊界；API沒有新點數上限。
時鐘在實體baseline前登記；更早規劃的總wall time未量測，圖像工具19.6秒另存，
不把新時鐘宣稱為完整委託的累計時間。commit、push held。

## 本次圖像生成 prompt

```text
Use case: stylized-concept. Asset type: one clean reference image for image-to-3D reconstruction of a replaceable game-character RIGHT leather glove for a young anime swordsman. Primary request: show EXACTLY ONE isolated anatomically credible empty right glove in a neutral open-hand bind pose, a single object and a single view, centered on pure white background. Fingertips point upward, wrist opening downward, palm facing the camera in a mild 15-degree three-quarter view; all five digits clearly visible. Four fingers are naturally straight with slight relaxed bend, modest separation and complete rounded fingertips; the opposable thumb projects clearly away from the palm on the viewer's right with a thick smooth thenar root and readable webbing. The glove must have realistic human hand proportions: middle finger longest, index and ring slightly shorter, little finger shortest; each finger has articulated knuckle volume and leather folds at the actual joints, no hard ridges over flexion zones. Brown medium-tone leather, subdued dark brown seams, subtle wear, no gold, no steel armor or fabric sleeve. Wrist is a short circular leather cuff with an obviously hollow opening, thin rolled edge and a single restrained seam; no long forearm. Sculptural, clean stylized 3D game-art render consistent with Ragnarok swordsman brown leather equipment, soft even diffuse studio illumination, geometry readable without painted shadows. Composition: entire glove with generous white margin, no cropping, no ground plane, no cast shadow, no labels, no second glove, no inset, no sword, no person, no grid, no panel layout. Avoid fused digits, extra digits, mitten forms, flat paper-like palm, star-shaped thumb port, extreme wide palm, ornate armor, black background, cinematic lighting and text.
```

設計圖是原創生成輸入，已保存repo內，沒有以程式修改像素。
