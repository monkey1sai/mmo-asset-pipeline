# r010 作者握姿與有限修正形變

來源為 r009 保存的無受測穿面 C-wrap；完整角色來源、原品質標準、接觸門檻與所有舊歷史保留。
這是右手局部前置製作。完整角色＋劍上限60,000tri、2K貼圖、1.74m、300幀／60fps連續技能規格未改。
本階段先驗904點手部與實際未縮放劍，不把局部成果稱作全角色交付。

## 設計

四指沿柄形成C形包握；指腹朝向柄，拇指維持已有對掌姿態。每指接觸應由整片指腹形體提供。
固定掌／側／背相機沿用原診斷尺度；先檢輪廓與接觸，再做形變，沒有細節雕刻／重拓樸。
現有完整pad法線：ring41、index26個點朝向柄（dot>.25），不支持更換遮罩；thumb仍需個別視覺判斷。

v001分配較深ring/index遠端彎曲，觸發28處真實手—劍穿面，保存並失敗。不能在此錯誤控制上補形。
下一來源選回原r009安全握姿；ring/index整片palmar phalange使用平滑normal field，保留指節長度、背面輪廓、腕／掌與203thumb。
作用於原semantic body，近柄安全幅度限制適用整片表面，不能只選最近三點。固定五個pad始終原樣驗收。
形變先反推穩定LBS，再寫可關閉shape key；不把posed delta直接放到rest座標，亦不改Basis。

## 技能與工具

art-engineer負責需求、可追溯實驗與交付狀態；rigging負責控制／skin；Blender director負責brief、固定視角；
sculpting只採主形與局部inflate的設計原則，無Dyntopo、Multires或新增面流；後續export-pipeline驗morph／skin回讀。
当前無Blender MCP callable；使用已實測本機Blender4.5.5、停用autoexec的背景CLI執行腳本。
預設shell sandbox provisioning failed是ENVIRONMENT_FAILURE；每個完整命令另經review，不改安全設定。

## 前置與停止

最多4新候選、每輪6h／總48h，包含準備、審查、等待、測試；原r0094/4不重開。310個r008/r009檔案已綁SHA。
形變最大rest4mm、grasp3mm；固定原Basis邊長ratio .25..3，只是保守guard不是體積藝術PASS。
完整面交叉／樣本深穿入、指腹形體、source身分、UV／權重／原骨及區域外零額外位移都要驗。
端點若通過，建立真實劍骨跟隨，局部61幀／60fps frame31起握持，逐幀及半幀驗；不事後改建立時刻。
匯出形變權重需有實際動畫，freshBLEND／GLB逐點回讀；這些都不代替完整300幀委託。
新增API與credits0；不寫repo外、憑證或全域設定；stage／commit／push待使用者驗證。

before-plan Astra/high advisory已完成，Jev確定性observation f83457aa-091a-4e6c-aadf-4690f3767f14。
主要限制：骨控制與修形分開、LBS反推、原Basis分母、固定接觸階段、武器實際掛接及world座標一致。
route本身provider_called=false、executed=false，不是agent啟動或交付批准。
